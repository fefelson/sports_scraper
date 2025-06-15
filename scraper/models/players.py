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



class Player(Databaseable, Downloadable, Fileable, Normalizable, Processable):

    _fileType = "pickle"
    _fileAgent = get_file_agent(_fileType)
    _dbAgent = SQLAlchemyDatabaseAgent


    def __init__(self, leagueId: str):
        super().__init__()

        self.leagueId = leagueId
        self.set_file_agent(self._fileAgent)
        self._set_dbAgent(self._dbAgent)

        self.logger = get_logger()


    def download(self, playerId: str) -> Dict[str, Any]:
        downloadAgent = get_download_agent(self.leagueId)
        return downloadAgent.fetch_player(self.leagueId, playerId)


    def load_from_db(self):
        """Loads data from the database into dataclass object using and returns it."""
        print(f"Databaseable.load_from_db called ")
        raise NotImplementedError


    def normalize(self, webData: dict) -> Dict[str, Any]:
        normalAgent = get_normal_agent(self.leagueId, webData["provider"])
        return normalAgent.normalize_player(webData)


    def process(self, playerId: str) :
        self.logger.debug("processing Player")
        
        self.set_file_path(playerId)
        if self.file_exists():
            webData = self.read_file()
            # player = self.normalize(webData)
        else:
            webData = self.download(playerId)
            self.write_file(webData)
            # player = self.normalize(webData) 
            # self.save_to_db(player)   
    

    def save_to_db(self, player: "Player"):
        """Saves self.data to the database."""
        try:
            self.dbAgent.insert_player(player)
        except Exception as e:
            # Catch unexpected errors
            self.logger.error(f"Failed to save boxscore to db: Unexpected error - {type(e).__name__}: {str(e)}")
            # raise  # Optional: re-raise for debugging
        else:
            # Runs if no exception occurs
            self.logger.info("Boxscore saved to db successfully")
        # Optional: Add a finally block if you need cleanup
        


    def set_file_path(self, playerId: str):
        ext = self.fileAgent.get_ext()
        playerId = playerId.split(".")[-1]
        playerPath = f"/{self.leagueId.lower()}/players/{playerId}.{ext}"
        self.filePath = basePath+playerPath

    
