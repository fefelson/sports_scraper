from abc import ABC, abstractmethod
from typing import Any, Optional
from itertools import chain

from ..database.models.database import engine, get_db_session
from ..database.models import Game, Player, Stadium, Team

from ..utils.logging_manager import get_logger

#################################################################
#################################################################


class Databaseable(ABC):


    def __init__(self, dbAgent: Optional["DatabaseAgent"]=None):
        self.dbAgent = dbAgent # Handles database operations


    def _set_dbAgent(self, dbAgent: "DatabaseAgent"):
        self.dbAgent = dbAgent


    @abstractmethod
    def save_to_db(self, data: Any):
        """Saves self.data to the database."""
        raise NotImplementedError   



    @abstractmethod
    def load_from_db(self) -> Any:
        """Loads data from the database into dataclass object using and returns it."""
        raise NotImplementedError  



###################################################################
###################################################################


class DatabaseAgent(ABC):
    """Abstract interface for database operations."""
    
    @abstractmethod
    def insert_boxscores(self, dataList: "BoxscoreData"):
        raise NotImplementedError


    @abstractmethod
    def insert_player(self, dataList: "BoxscoreData"):
        raise NotImplementedError


###################################################################
###################################################################


class SQLAlchemyDatabaseAgent(DatabaseAgent):
    """SQLAlchemy implementation of the IDatabaseAgent interface."""

    def _flatten(items):
        """Recursively flatten misc, yielding individual SQLAlchemy objects."""
        if items is None:  # Handle None case
            return
        for item in items:
            if isinstance(item, list):
                yield from SQLAlchemyDatabaseAgent._flatten(item)  # Recurse into nested lists
            else:
                yield item  # Yield individual objects


    @staticmethod
    def insert_boxscore(boxscore: "BoxscoreData") -> None:
        """Insert boxscore data into the database."""
        logger = get_logger()

        with get_db_session() as session:
            # Insert Stadiums with check
            if not session.query(Stadium).filter_by(stadium_id=boxscore.stadium.stadium_id).first():
                session.add(boxscore.stadium)

            # Insert Teams with check
            for team in boxscore.teams:
                if not session.query(Team).filter_by(team_id=team.team_id).first():
                    session.add(team)

            # Insert Players with check
            for player in boxscore.players:
                if not session.query(Player).filter_by(player_id=player.player_id).first():
                    session.add(player)

            # Insert Games with check
            # If there is a redundant game_id in Games don't bother inserting anything else
            if not session.query(Game).filter_by(game_id=boxscore.game.game_id).first():
                session.add(boxscore.game)
                if boxscore.overUnders:
                    session.add(boxscore.overUnders)
                # List-based fields including misc
                list_fields = [
                    boxscore.teamStats,
                    boxscore.playerStats,
                    boxscore.periods,
                    boxscore.gameLines if boxscore.gameLines is not None else [],
                    boxscore.lineups if boxscore.lineups is not None else [],
                    boxscore.misc if boxscore.misc is not None else []
                ]

                # Chain the flattened fields
                all_list_objects = chain(*(SQLAlchemyDatabaseAgent._flatten(field) for field in list_fields))

                # Add all list objects at once
                session.add_all(all_list_objects)
            else:
                logger.warning(f"Game {boxscore.game.game_id} already in db")
