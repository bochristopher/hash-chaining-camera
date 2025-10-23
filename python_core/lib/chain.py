"""
Hash chain storage and management using SQLAlchemy
Stores provenance chain with cryptographic integrity
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()


class ChainEntry(Base):
    """
    Database model for chain entries
    """
    __tablename__ = 'chain_entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    index = Column(Integer, unique=True, nullable=False, index=True)
    timestamp = Column(String(32), nullable=False)
    frame_path = Column(String(512), nullable=False)
    frame_hash = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False)
    signature = Column(String(256), nullable=False)
    metadata = Column(Text, nullable=True)  # JSON-encoded metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary"""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "frame_path": self.frame_path,
            "frame_hash": self.frame_hash,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
            "signature": self.signature,
            "metadata": json.loads(self.metadata) if self.metadata else {}
        }


class ProvenanceChain:
    """
    Manages the provenance hash chain with database persistence
    """

    def __init__(self, db_path: Path):
        """
        Initialize chain storage

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create database engine
        self.engine = create_engine(
            f'sqlite:///{self.db_path}',
            echo=False
        )

        # Create tables
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def add_entry(
        self,
        index: int,
        timestamp: str,
        frame_path: Path,
        frame_hash: str,
        previous_hash: str,
        entry_hash: str,
        signature: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChainEntry:
        """
        Add new entry to the chain

        Args:
            index: Chain index
            timestamp: ISO timestamp
            frame_path: Path to frame image
            frame_hash: SHA-256 of frame
            previous_hash: Hash of previous entry
            entry_hash: Hash of this entry
            signature: Ed25519 signature
            metadata: Optional sensor/context data

        Returns:
            Created ChainEntry
        """
        session = self.get_session()

        try:
            entry = ChainEntry(
                index=index,
                timestamp=timestamp,
                frame_path=str(frame_path),
                frame_hash=frame_hash,
                previous_hash=previous_hash,
                entry_hash=entry_hash,
                signature=signature,
                metadata=json.dumps(metadata) if metadata else None
            )

            session.add(entry)
            session.commit()
            session.refresh(entry)

            return entry

        finally:
            session.close()

    def get_entry_by_index(self, index: int) -> Optional[ChainEntry]:
        """
        Get entry by chain index

        Args:
            index: Chain index

        Returns:
            ChainEntry or None
        """
        session = self.get_session()
        try:
            return session.query(ChainEntry).filter(
                ChainEntry.index == index
            ).first()
        finally:
            session.close()

    def get_latest_entry(self) -> Optional[ChainEntry]:
        """
        Get the most recent chain entry

        Returns:
            Latest ChainEntry or None
        """
        session = self.get_session()
        try:
            return session.query(ChainEntry).order_by(
                ChainEntry.index.desc()
            ).first()
        finally:
            session.close()

    def get_all_entries(self) -> List[ChainEntry]:
        """
        Get all chain entries in order

        Returns:
            List of ChainEntry objects
        """
        session = self.get_session()
        try:
            return session.query(ChainEntry).order_by(
                ChainEntry.index.asc()
            ).all()
        finally:
            session.close()

    def get_chain_length(self) -> int:
        """
        Get total number of entries in chain

        Returns:
            Chain length
        """
        session = self.get_session()
        try:
            return session.query(ChainEntry).count()
        finally:
            session.close()

    def export_to_json(self, output_path: Path) -> None:
        """
        Export entire chain to JSON file

        Args:
            output_path: Path for JSON export
        """
        entries = self.get_all_entries()
        chain_data = [entry.to_dict() for entry in entries]

        with open(output_path, 'w') as f:
            json.dump(chain_data, f, indent=2)

        print(f"Exported {len(chain_data)} entries to {output_path}")

    def import_from_json(self, input_path: Path) -> int:
        """
        Import chain from JSON file

        Args:
            input_path: Path to JSON file

        Returns:
            Number of entries imported
        """
        with open(input_path, 'r') as f:
            chain_data = json.load(f)

        session = self.get_session()
        count = 0

        try:
            for entry_dict in chain_data:
                # Check if entry already exists
                existing = session.query(ChainEntry).filter(
                    ChainEntry.index == entry_dict["index"]
                ).first()

                if not existing:
                    entry = ChainEntry(
                        index=entry_dict["index"],
                        timestamp=entry_dict["timestamp"],
                        frame_path=entry_dict["frame_path"],
                        frame_hash=entry_dict["frame_hash"],
                        previous_hash=entry_dict["previous_hash"],
                        entry_hash=entry_dict["entry_hash"],
                        signature=entry_dict["signature"],
                        metadata=json.dumps(entry_dict.get("metadata"))
                    )
                    session.add(entry)
                    count += 1

            session.commit()
            print(f"Imported {count} new entries from {input_path}")
            return count

        finally:
            session.close()
