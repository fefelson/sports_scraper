import os
import re
from difflib import get_close_matches
from pprint import pprint 

from ..src.capabilities.fileable import PickleAgent
from ..src.database.models.baseball import BattingOrder, Bullpen, BaseballTeamStat, Pitch, AtBat 
from ..src.database.models.core import Game, Period, Player, ProviderMapping, Team, Stadium
from ..src.database.models.gaming import GameLine, OverUnder
from ..src.sports.leagues import MLB
from ..src.providers.espn.normalizers.espn_mlb_normalizer import ESPNMLBNormalizer
from ..src.providers.yahoo.normalizers.yahoo_mlb_normalizer import YahooMLBNormalizer

from ..src.database.models.database import get_db_session


BASE_PATH = os.environ["HOME"] + "/FEFelson/leagues/mlb/boxscores/"


def merge_game(yahooBox, espnBox):
    game = yahooBox["game"]
    with get_db_session() as session:
        # Insert Game with check
        if not session.query(Game).filter_by(game_id=game["game_id"]).first():
            session.add(Game(**game))
            try:
                for batter in yahooBox["lineups"]["batting"]:
                    if session.query(Player).filter_by(player_id=batter["player_id"]).first():
                        session.add(BattingOrder(**batter))
            except KeyError:
                pass 
            try:
                for pitcher in yahooBox["lineups"]["pitching"]:
                    if session.query(Player).filter_by(player_id=pitcher["player_id"]).first():
                        session.add(Bullpen(**pitcher))
            except KeyError:
                pass


            for provider, box in (("yahoo", yahooBox), ("espn", espnBox)):
                if box is not None:
                    mappings = {
                            "provider": provider,
                            "entity_type": "game",
                            "entity_id": yahooBox["game"]["game_id"],
                            "provider_id": box["game"]["game_id"]
                    }
                    existing = session.query(ProviderMapping).filter(
                        ProviderMapping.provider == mappings["provider"],
                        ProviderMapping.entity_type == mappings["entity_type"],
                        ProviderMapping.entity_id == mappings["entity_id"]
                    ).first()

                    if not existing:
                        session.add(ProviderMapping(**mappings))


def merge_stadium(yahooBox, espnBox):
    yahoo = yahooBox["stadium"]
    
    if espnBox:
        espn = espnBox["stadium"]
        if (yahoo.get("name") is None or yahoo["name"] == "") and (espn.get("name") is not None and espn["name"] != ""):
            yahoo["name"] = espn["name"]

    with get_db_session() as session:
        # Insert Stadiums with check
        if not session.query(Stadium).filter_by(stadium_id=yahoo["stadium_id"]).first():
            session.add(Stadium(**yahoo))



def map_players(yahooBox, espnBox):

    yahoo_by_name = {f"{p['first_name'].lower()} {p['last_name'].lower()}": p["player_id"] for p in yahooBox["players"]}
    mapping = {}

    for espn_player in[ab[index] for ab in espnBox["misc"]["at_bats"] for index in ("batter_id", "pitcher_id")]:
        name = espn_player.lower()
        match = get_close_matches(name, yahoo_by_name.keys(), n=1, cutoff=0.7)
        
        if match:
            mapping[espn_player.lower()] = yahoo_by_name[match[0]]
            
        else:
            # Flag for review
            print(f"No match found for ESPN player: {espn_player}")

    return mapping


def merge_teams(yahooBox, espnBox):
    teams = []
    mappings = []
    for yahoo in yahooBox["teams"]:
        team = Team(**yahoo)
        teams.append(team)
        for provider, box in (("yahoo", yahooBox), ("espn", espnBox)):
            if box is not None:
                for boxTeam in box["teams"]:
                    if boxTeam["team_id"] == team.team_id:
                        mappings.append(
                            ProviderMapping(
                                provider=provider,
                                entity_type="team",
                                entity_id=team.team_id,
                                provider_id=boxTeam["team_id"]
                            ))
    return teams, mappings
 

def merge_players(yahooBox, espnBox):
    players = []
    mappings = []
    playerMappings = None
    if espnBox:
        try:
            playerMappings = map_players(yahooBox, espnBox)
        except TypeError:
            pass

    for yahoo in yahooBox["players"]:
        player = Player(**yahoo)
        players.append(player)

        mappings.append(
            ProviderMapping(
                provider="yahoo",
                entity_type="player",
                entity_id=player.player_id,
                provider_id=yahoo["player_id"]
            ))
    if playerMappings is not None:
        for espn in espnBox["players"]:

            if playerMappings.get(espn["dspNm"].lower()):
                mappings.append(
                    ProviderMapping(
                        provider="espn",
                        entity_type="player",
                        entity_id=player.player_id,
                        provider_id=espn["id"]
                    )) 
                    
    return players, mappings


def game_lines(yahooBox):
    if yahooBox.get("gameLines"):
        with get_db_session() as session:
            for gl in yahooBox["gameLines"]:
                # Insert Game with check
                existing = session.query(GameLine).filter(
                            GameLine.game_id == gl["game_id"],
                            GameLine.team_id == gl["team_id"]
                        ).first()
                if not existing:
                    session.add(GameLine(**gl))


def over_under(yahooBox):
    if yahooBox.get("overUnder"):
        with get_db_session() as session:
            if not session.query(OverUnder).filter_by(game_id=yahooBox["overUnder"]["game_id"]).first():
                session.add(OverUnder(**yahooBox["overUnder"]))


def set_periods(yahooBox):
    periods = []
    for p in yahooBox["periods"]:
        try:
            int(p["pts"])
            periods.append(p)
        except ValueError:
            pass
    
    with get_db_session() as session:
        for p in periods:
            # Insert Period with check
            existing = session.query(Period).filter(
                        Period.game_id == p["game_id"],
                        Period.team_id == p["team_id"],
                        Period.period == p["period"]
                    ).first()
            if not existing:
                session.add(Period(**p))


def team_stats(yahooBox, espnBox):
    game = yahooBox["game"]

    teamStats = []
    if espnBox:
        for espn in espnBox["teamStats"]:
            teamStats.append( {"game_id": game["game_id"], 
                    "team_id": espn["team_id"],
                    "opp_id": game["home_id"] if espn["team_id"] == game["away_id"] else game["away_id"],
                    "runs": espn["batting"]["r"],
                    "hits": espn["batting"]["h"],
                    "errors": espn["errors"]
                    })
    with get_db_session() as session:
        for stats in teamStats:
            existing = session.query(BaseballTeamStat).filter(
                        BaseballTeamStat.game_id == stats["game_id"],
                        BaseballTeamStat.team_id == stats["team_id"]
                    ).first()
            if not existing:
                session.add(BaseballTeamStat(**stats))


def at_bats(yahooBox, espnBox, session):
    # playerMappings = map_players(yahooBox, espnBox)
    yahoo = yahooBox["misc"]["at_bats"]

            # Insert Game with check
    for ab in yahoo:
        session.add(AtBat(**ab))    



def pitch_track(yahooBox, espnBox, session):
    pitches = []
    try:
        playerMappings = map_players(yahooBox, espnBox)
        yahoo = yahooBox["game"]
        espn = espnBox["misc"]["pitches"]
        for pitch in espn:
            pitch["game_id"] = yahoo["game_id"]
            pitch["batter_id"] = playerMappings[pitch["batter_id"].lower()]
            pitch["pitcher_id"] = playerMappings[pitch["pitcher_id"].lower()]
            pitches.append(pitch)
    except (TypeError, KeyError):
        pass 
   
    for p in pitches:
        session.add(Pitch(**p))



def main():
    boxscore = MLB().boxscore
    
    for gamePath, providers, _ in os.walk(f"{BASE_PATH}"):
        
        if re.match(r".*/(\d{4})/(\d{2})/(\d{2})$", gamePath):
            with get_db_session() as session:
                for gameId in [gameId for gameId in providers if gameId != "espn"]:
                    print(gamePath)
                    
                    yahooBox =YahooMLBNormalizer("MLB").normalize_boxscore(PickleAgent.read(f"{gamePath}/{gameId}/yahoo.pkl"))
                    try:
                        espnBox = ESPNMLBNormalizer("MLB").normalize_boxscore(PickleAgent.read(f"{gamePath}/{gameId}/espn.pkl"))
                    except FileNotFoundError:
                        espnBox = None

                    for func in (merge_stadium, merge_game):
                        func(yahooBox, espnBox)
                        
                    for func in (game_lines, set_periods):
                        func(yahooBox)
                        
                    for func in (team_stats, ):
                        func(yahooBox, espnBox)

                    for func in (at_bats, pitch_track):
                        func(yahooBox, espnBox, session)



                

               
           

if __name__ == "__main__":
    main()