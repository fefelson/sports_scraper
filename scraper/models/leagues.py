from typing import List

from .boxscores import Boxscore
from .matchups import Matchup
from .players import Player
from .scoreboards import Scoreboard
from ..capabilities import Processable, Updateable
from ..utils.logging_manager import get_logger


################################################################################
################################################################################


class League(Processable, Updateable):

    _leagueId = None
    _leagueConfig = None
    _analytics = None
    _schedule = None

    def __init__(self):
        super().__init__()
        
        self.boxscore = Boxscore(self._leagueId)
        self.matchup = Matchup(self._leagueId)
        self.player = Player(self._leagueId)
        self.scoreboard = Scoreboard(self._leagueId)
        # self.team = Team(self._leagueId)

        self.logger = get_logger()


    def get_current_season(self) -> int:
        return self._leagueConfig.get("current_season")


    def is_active(self) -> bool:
        return self._schedule.is_active(self._leagueConfig)


    def analyze(self) -> None:
        if self.is_active():
            self.logger.info(f"{self._leagueId} Analytics")

            season = self._leagueConfig.get("current_season")
            teamStats = self._analytics.fetch_team_stats(season)
            teamGaming = self._analytics.fetch_team_gaming(season)
            teamStatModels = self._analytics.team_averages_adjusted(teamStats)
            teamGamingModels = self._analytics.team_gaming_averages(teamGaming)

            self._analytics.truncate_tables()
            for models in (teamStatModels, teamGamingModels):
                self._analytics.store_models(models)


    def get_matchups(self, gameDate: str) -> List[dict]:
        return [self.matchup.process(game) for game in self.scoreboard.process(gameDate) if game["statusType"] ==  "pregame" and game["gameType"] not in ("preseason", "spring training")]                    


    def needs_update(self):
        return self.is_active() and self._schedule.is_uptodate(self._leagueConfig)


    def process(self, gameDate):
        self.logger.info(f"{self._leagueId} processing {gameDate}")
        
        for provider in ("yahoo", "espn"):
            for game in self.scoreboard.process(gameDate, provider):
                if game["gameType"] not in ("preseason", "spring training"):
                    if game["statusType"] == "final":
                        self.boxscore.process(game)
                    elif game["statusType"] == "pregame":
                        self.matchup.process(game)
                    

    def update(self):
        if self.needs_update():
            self.logger.info(f"Updating {self._leagueId}")
            for gameDate in self._schedule.process(self._leagueConfig):
                self.process(gameDate)
                self._leagueConfig.set("last_update", gameDate)
                self._leagueConfig._write_config()
                self.logger.info(f"{self._leagueId} current up until {gameDate}")
            self.analyze()

        for gameDate in self._schedule.process(self._leagueConfig, nGD=2):
            self.process(gameDate)        
            self.logger.debug(f"{self._leagueId} matchups processed for {gameDate}")
        
        self.logger.debug(f"{self._leagueId} is up to date")
