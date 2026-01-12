"""
Database models for AI Competitor Watchdog
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()


class Competitor(Base):
    """Competitor company"""
    __tablename__ = 'competitors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    base_url = Column(String(512), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationships
    assets = relationship("Asset", back_populates="competitor", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Competitor(name='{self.name}', base_url='{self.base_url}')>"


class Asset(Base):
    """Web asset to monitor (pricing page, features page, etc.)"""
    __tablename__ = 'assets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)
    asset_type = Column(String(50), nullable=False)  # pricing, features, changelog, etc.
    url = Column(String(1024), nullable=False)
    crawl_frequency = Column(String(20), nullable=False)  # daily, weekly
    priority_threshold = Column(String(20))  # high, medium, low
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationships
    competitor = relationship("Competitor", back_populates="assets")
    snapshots = relationship("Snapshot", back_populates="asset", cascade="all, delete-orphan")
    changes = relationship("Change", back_populates="asset", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_competitor_url', 'competitor_id', 'url', unique=True),
    )
    
    def __repr__(self):
        return f"<Asset(competitor_id={self.competitor_id}, type='{self.asset_type}', url='{self.url}')>"


class Snapshot(Base):
    """Content snapshot of an asset at a point in time"""
    __tablename__ = 'snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA256 hash
    content_text = Column(Text)  # Extracted clean text
    content_html = Column(Text)  # Raw HTML (optional, for debugging)
    metadata_json = Column('metadata', JSON)  # Structured data (pricing tiers, features, etc.) - using metadata_json to avoid SQLAlchemy reserved name
    crawl_timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    http_status = Column(Integer)  # HTTP status code
    
    # Relationships
    asset = relationship("Asset", back_populates="snapshots")
    changes_before = relationship("Change", foreign_keys="Change.snapshot_before_id", back_populates="snapshot_before")
    changes_after = relationship("Change", foreign_keys="Change.snapshot_after_id", back_populates="snapshot_after")
    
    __table_args__ = (
        Index('idx_asset_timestamp', 'asset_id', 'crawl_timestamp'),
        Index('idx_content_hash', 'content_hash'),
    )
    
    def __repr__(self):
        return f"<Snapshot(asset_id={self.asset_id}, hash='{self.content_hash[:8]}...', timestamp={self.crawl_timestamp})>"


class Change(Base):
    """Detected change between two snapshots"""
    __tablename__ = 'changes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    snapshot_before_id = Column(Integer, ForeignKey('snapshots.id'), nullable=False)
    snapshot_after_id = Column(Integer, ForeignKey('snapshots.id'), nullable=False)
    change_type = Column(String(50))  # pricing, feature, compliance, etc.
    priority = Column(String(20))  # high, medium, low
    summary = Column(Text)  # ≤3 sentences
    why_it_matters = Column(Text)
    before_content = Column(Text)
    after_content = Column(Text)
    diff_metadata_json = Column('diff_metadata', JSON)  # Structured diff data
    detected_at = Column(TIMESTAMP, default=datetime.utcnow)
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(TIMESTAMP)
    
    # Relationships
    asset = relationship("Asset", back_populates="changes")
    snapshot_before = relationship("Snapshot", foreign_keys=[snapshot_before_id], back_populates="changes_before")
    snapshot_after = relationship("Snapshot", foreign_keys=[snapshot_after_id], back_populates="changes_after")
    alerts = relationship("Alert", back_populates="change", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Change(asset_id={self.asset_id}, type='{self.change_type}', priority='{self.priority}')>"


class Alert(Base):
    """Alert sent for a change"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    change_id = Column(Integer, ForeignKey('changes.id'), nullable=False)
    priority = Column(String(20), nullable=False)
    slack_message_id = Column(String(255))  # For tracking (if available)
    sent_at = Column(TIMESTAMP, default=datetime.utcnow)
    delivery_type = Column(String(50))  # immediate, daily_digest, weekly_summary
    
    # Relationships
    change = relationship("Change", back_populates="alerts")
    
    def __repr__(self):
        return f"<Alert(change_id={self.change_id}, priority='{self.priority}', type='{self.delivery_type}')>"

