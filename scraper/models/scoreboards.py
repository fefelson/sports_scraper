from typing import List
from ..capabilities.fileable import JSONAgent
from ..capabilities import Downloadable, Normalizable, Processable
from ..providers import get_download_agent, get_normal_agent # factory methods
from ..utils.logging_manager import get_logger


####################################################################
####################################################################


class Scoreboard(Downloadable, Normalizable, Processable):

    def __init__(self, leagueId: str):
        self.leagueId = leagueId
        self.logger = get_logger()


    def normalize(self, webData: dict) -> dict:
        normalAgent = get_normal_agent(self.leagueId, webData["provider"])
        return normalAgent.normalize_scoreboard(webData)


    def process(self, gameDate: str, provider) -> List[dict]:
        self.logger.debug(f"{self.leagueId} Scoreboard processing {gameDate}")
                
        webData = self.download(gameDate, provider)
        scoreboard = self.normalize(webData)
        return scoreboard["games"]


    def download(self, gameDate, provider):
        downloadAgent = get_download_agent(self.leagueId, provider)
        return downloadAgent.fetch_scoreboard(self.leagueId, gameDate)

    
