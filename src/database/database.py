"""
Database connection management and CRUD operations for SQLite database.
"""

import logging
from pathlib import Path
from typing import Optional, Type, List, Any, Dict
from contextlib import contextmanager

from sqlalchemy import create_engine, event, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine

from src.database.models import Base, Space, Proposal, Vote

class DatabaseManager:
    """Manages database connections and CRUD operations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize database manager with configuration."""
        self.config = config['database']
        self.db_path = Path(self.config['path'])
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create engine with configuration
        self.engine = self._create_engine()
        
        # Create session factory
        self.Session = sessionmaker(bind=self.engine)
        
        # Initialize database
        self._initialize_database()
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with proper configuration."""
        engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=self.config['connection'].get('echo', False),
            pool_size=self.config['connection'].get('pool_size', 5),
            max_overflow=self.config['connection'].get('max_overflow', 10),
            pool_timeout=self.config['connection'].get('pool_timeout', 30)
        )
        
        # Configure SQLite for better performance
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            pragmas = self.config['performance']['pragma']
            
            for pragma, value in pragmas.items():
                cursor.execute(f"PRAGMA {pragma}={value}")
            cursor.close()
        
        return engine
    
    def _initialize_database(self) -> None:
        """Create database tables if they don't exist."""
        Base.metadata.create_all(self.engine)
        logging.info("Database initialized successfully")
    
    @contextmanager
    def session_scope(self) -> Session:
        """Provide a transactional scope around operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logging.error(f"Database error: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_or_create(
        self,
        session: Session,
        model: Type[Base],
        **kwargs
    ) -> tuple[Base, bool]:
        """
        Get an existing record or create a new one.
        
        Args:
            session: Database session
            model: Model class
            **kwargs: Fields to query/create with
            
        Returns:
            Tuple of (instance, created) where created is a boolean
        """
        instance = session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False
        
        instance = model(**kwargs)
        try:
            session.add(instance)
            session.flush()
            return instance, True
        except SQLAlchemyError:
            session.rollback()
            return session.query(model).filter_by(**kwargs).first(), False
    
    def bulk_insert_or_update(
        self,
        items: List[Base],
        check_exists: bool = True
    ) -> None:
        """
        Bulk insert or update records.
        
        Args:
            items: List of model instances to insert/update
            check_exists: Whether to check for existing records
        """
        with self.session_scope() as session:
            for item in items:
                if check_exists:
                    existing = session.query(type(item)).filter_by(id=item.id).first()
                    if existing:
                        # Update existing record
                        for key, value in item.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing, key, value)
                    else:
                        session.add(item)
                else:
                    session.add(item)
    
    def save_space(self, space: Space, check_exists: bool = True) -> None:
        """Save a space record."""
        with self.session_scope() as session:
            if check_exists:
                existing = session.query(Space).filter_by(id=space.id).first()
                if existing:
                    # Update fields
                    existing.name = space.name
                    existing.about = space.about
                    existing.network = space.network
                    existing.symbol = space.symbol
                    existing.members = space.members
                    existing.proposals_count = space.proposals_count
                    existing.followers = space.followers
                    existing.raw_data = space.raw_data
                else:
                    session.add(space)
            else:
                session.add(space)
    
    def save_proposal(self, proposal: Proposal, check_exists: bool = True) -> None:
        """Save a proposal record."""
        with self.session_scope() as session:
            if check_exists:
                existing = session.query(Proposal).filter_by(id=proposal.id).first()
                if existing:
                    # Update fields
                    existing.title = proposal.title
                    existing.body = proposal.body
                    existing.choices = proposal.choices
                    existing.start = proposal.start
                    existing.end = proposal.end
                    existing.state = proposal.state
                    existing.votes_count = proposal.votes_count
                    existing.scores_total = proposal.scores_total
                    existing.raw_data = proposal.raw_data
                else:
                    session.add(proposal)
            else:
                session.add(proposal)
    
    def save_votes(self, votes: List[Vote], check_exists: bool = True) -> None:
        """Save multiple vote records."""
        with self.session_scope() as session:
            for vote in votes:
                if check_exists:
                    existing = session.query(Vote).filter_by(id=vote.id).first()
                    if existing:
                        # Update fields
                        existing.choice = vote.choice
                        existing.voting_power = vote.voting_power
                        existing.raw_data = vote.raw_data
                    else:
                        session.add(vote)
                else:
                    session.add(vote)
    
    def get_space_by_id(self, space_id: str) -> Optional[Space]:
        """Get a space by ID."""
        with self.session_scope() as session:
            return session.query(Space).filter_by(id=space_id).first()
    
    def get_proposal_by_id(self, proposal_id: str) -> Optional[Proposal]:
        """Get a proposal by ID."""
        with self.session_scope() as session:
            return session.query(Proposal).filter_by(id=proposal_id).first()
    
    def get_votes_for_proposal(self, proposal_id: str) -> List[Vote]:
        """Get all votes for a proposal."""
        with self.session_scope() as session:
            return session.query(Vote).filter_by(proposal_id=proposal_id).all()
    
    def get_proposal_count(self) -> int:
        """Get total number of proposals."""
        with self.session_scope() as session:
            return session.query(Proposal).count()
    
    def get_vote_count(self) -> int:
        """Get total number of votes."""
        with self.session_scope() as session:
            return session.query(Vote).count()
    
    def delete_space(self, space_id: str) -> bool:
        """Delete a space and all related records."""
        with self.session_scope() as session:
            space = session.query(Space).filter_by(id=space_id).first()
            if space:
                session.delete(space)
                return True
            return False