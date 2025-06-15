from datetime import datetime, timedelta
import os
import pytz

from ..capabilities import Fileable, Normalizable, Processable, Downloadable
from ..capabilities.fileable import get_file_agent
from ..providers import get_download_agent, get_normal_agent
from ..utils.logging_manager import get_logger

######################################################################
######################################################################


basePath = os.path.join(os.environ["HOME"], "FEFelson/Sports")
est = pytz.timezone('America/New_York')


######################################################################
######################################################################


class Matchup(Downloadable, Fileable, Normalizable, Processable):

    _fileType = "pickle"
    _fileAgent = get_file_agent(_fileType)


    def __init__(self, leagueId: str):
        super().__init__()

        self.leagueId = leagueId
        self.logger = get_logger()
        self.set_file_agent(self._fileAgent)


    def download(self, matchup: dict) -> dict:
        download_agent = get_download_agent(self.leagueId, matchup["provider"])
        return download_agent.fetch_boxscore(matchup["url"])


    def needs_update(self, matchup: dict):
        return (datetime.fromisoformat(matchup["gameTime"])- datetime.now().astimezone(est) < timedelta(hours=3)) and not matchup["lineups"]


    def normalize(self, webData: dict) -> dict:
        normalAgent = get_normal_agent(self.leagueId, webData["provider"])
        return normalAgent.normalize_matchup(webData)


    def process(self, game: dict) -> dict:
        self.logger.info("process Matchup")
        
        self.set_file_path(game)
        if self.file_exists():
            matchup = self.read_file()
            if self.needs_update(matchup):
                self.update(matchup)
            else:
                [matchup["odds"].append(odds) for odds in game["odds"]]
        else:
            matchup = self.update(game)
        self.write_file(matchup)
        return matchup
    
 
    def set_file_path(self, game: dict):
        # module_dir = os.path.dirname(os.path.abspath(__file__))
         
        if game.get("week"):
            gamePath = f"/{self.leagueId.lower()}/matchups/{game['season']}/{game['week']}/{game['gameId'].split('.')[-1]}.{ext}"
        else:
            gamePath = f"/{self.leagueId.lower()}/matchups/{game['season']}/{game['month']}/{game['day']}/{game['gameId'].split('.')[-1]}.{ext}"
        
        self.filePath = basePath+gamePath
    

    def update(self, matchup: dict) -> dict:
        if matchup["url"]:
                    
            webData = self.download()
            tempMatchup = self.normalize(webData)

            for index in ("players", "teams", "injuries", "lineups"):
                if tempMatchup[index]:
                    matchup[index] = tempMatchup[index]
            [matchup["odds"].append(odds) for odds in tempMatchup["odds"]]
        return matchup
    

   
    

