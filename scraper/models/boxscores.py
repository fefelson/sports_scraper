from datetime import datetime
from typing import Any, Dict
import os

from ..capabilities import Fileable, Normalizable, Processable, Downloadable, Databaseable
from ..capabilities.databaseable import SQLAlchemyDatabaseAgent
from ..capabilities.fileable import get_file_agent
from ..providers import get_download_agent, get_normal_agent
from ..utils.logging_manager import get_logger


######################################################################
######################################################################


basePath = os.path.join(os.environ["HOME"], "FEFelson/leagues")


######################################################################
######################################################################



class Boxscore(Databaseable, Downloadable, Fileable, Normalizable, Processable):

    _fileType = "pickle"
    _fileAgent = get_file_agent(_fileType)
    _dbAgent = SQLAlchemyDatabaseAgent


    def __init__(self, leagueId: str):
        super().__init__()

        self.leagueId = leagueId
        self.set_file_agent(self._fileAgent)
        

        self.logger = get_logger()


    def download(self, game: dict) -> Dict[str, Any]:
        downloadAgent = get_download_agent(self.leagueId, game["provider"])
        return downloadAgent.fetch_boxscore(game)


    def load_from_db(self):
        """Loads data from the database into dataclass object using and returns it."""
        print(f"Databaseable.load_from_db called ")
        raise NotImplementedError


    def normalize(self, webData: dict) -> Dict[str, Any]:
        normalAgent = get_normal_agent(self.leagueId, webData["provider"])
        return normalAgent.normalize_boxscore(webData)


    def process(self, game: dict) :
        self.logger.debug("processing Boxscore")
        
        self.set_file_path(game)
        if self.file_exists():
            webData = self.read_file()
            boxscore = self.normalize(webData)
        else:
            if game["url"]:
                webData = self.download(game)
                self.write_file(webData)
                boxscore = self.normalize(webData)
                self.save_to_db(boxscore)       
    

    def save_to_db(self, boxscore: dict):
        """Saves self.data to the database."""
        try:
            self._dbAgent.insert_boxscore(boxscore)
        except Exception as e:
            # Catch unexpected errors
            self.logger.error(f"Failed to save boxscore to db: Unexpected error - {type(e).__name__}: {str(e)}")
            # raise  # Optional: re-raise for debugging
        else:
            # Runs if no exception occurs
            self.logger.info("Boxscore saved to db successfully")
        # Optional: Add a finally block if you need cleanup
        


    def set_file_path(self, game: dict):
        if game.get("week"):
            gamePath = f"/{self.leagueId.lower()}/boxscores/{game['season']}/{game['week']}/{game['provider']}/{game['gameId'].split('.')[-1]}.{self._fileAgent.get_ext()}"
        else:
            month, day = str(datetime.fromisoformat(game["gameTime"]).date()).split("-")[1:]
            gamePath = f"/{self.leagueId.lower()}/boxscores/{game['season']}/{month}/{day}/{game['provider']}/{game['gameId'].split('.')[-1]}.{self._fileAgent.get_ext()}"  
        self.filePath = basePath+gamePath

    
