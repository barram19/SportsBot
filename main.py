import argparse
import requests
from datetime import datetime, timedelta
import time
from colorama import Fore, Style
import pandas as pd
import tensorflow as tf
from src.Predict import NN_Runner, XGBoost_Runner
from src.Utils.Dictionaries import team_index_current
from src.Utils.tools import create_todays_games_from_odds, get_json_data, to_data_frame, get_todays_games_json, create_todays_games
from src.DataProviders.SbrOddsProvider import SbrOddsProvider

todays_games_url=

# Replace <YOUR_API_KEY> with your actual API key
api_key = "8f283a0b9aa2f6e2b517c77b786bb1cb"

# Set the URL for the endpoint that returns odds data for MLB games
url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

# Set the query parameters for the request
params = {
    "apiKey": 8f283a0b9aa2f6e2b517c77b786bb1cb,
    "sport": "baseball_mlb",
    "region": "us",
    "mkt": "h2h",
}

# Make a GET request to the endpoint and retrieve the response
response = requests.get(url, params=params)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Print the response content in JSON format
    print(response.json())
else:
    # Print an error message
    print(f"Error {response.status_code}: {response.text}")
           
#todays_games_url = 'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=today.json'
#data_url = 'https://stats.nba.com/stats/leaguedashteamstats?' \
 #          'Conference=&DateFrom=&DateTo=&Division=&GameScope=&' \
  #         'GameSegment=&LastNGames=0&LeagueID=00&Location=&' \
   #        'MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&' \
    #       'PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&' \
     #      'PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&' \
      #     'Season=2022-23&SeasonSegment=&SeasonType=Regular+Season&ShotClockRange=&' \
       #    'StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision='


def createTodaysGames(games, df, odds):
    match_data = []
    todays_games_uo = []
    home_team_odds = []
    away_team_odds = []
    # todo: get the days rest for current games
    home_team_days_rest = []
    away_team_days_rest = []

    for game in games:
        home_team = game[0]
        away_team = game[1]
        if home_team not in team_index_current or away_team not in team_index_current:
            continue
        if odds is not None:
            game_odds = odds[home_team + ':' + away_team]
            todays_games_uo.append(game_odds['under_over_odds'])
            
            home_team_odds.append(game_odds[home_team]['money_line_odds'])
            away_team_odds.append(game_odds[away_team]['money_line_odds'])

        else:
            todays_games_uo.append(input(home_team + ' vs ' + away_team + ': '))

            home_team_odds.append(input(home_team + ' odds: '))
            away_team_odds.append(input(away_team + ' odds: '))
        
        # calculate days rest for both teams
        dateparse = lambda x: datetime.strptime(x, '%d/%m/%Y %H:%M')
        schedule_df = pd.read_csv('Data/nba-2022-UTC.csv', parse_dates=['Date'], date_parser=dateparse)
        home_games = schedule_df[(schedule_df['Home Team'] == home_team) | (schedule_df['Away Team'] == home_team)]
        away_games = schedule_df[(schedule_df['Home Team'] == away_team) | (schedule_df['Away Team'] == away_team)]
        last_home_date = home_games.loc[schedule_df['Date'] <= datetime.today()].sort_values('Date',ascending=False).head(1)['Date'].iloc[0]
        last_away_date = away_games.loc[schedule_df['Date'] <= datetime.today()].sort_values('Date',ascending=False).head(1)['Date'].iloc[0]
        home_days_off = timedelta(days=1) + datetime.today() - last_home_date
        away_days_off = timedelta(days=1) + datetime.today() - last_away_date
        # print(f"{away_team} days off: {away_days_off.days} @ {home_team} days off: {home_days_off.days}")

        home_team_days_rest.append(home_days_off.days)
        away_team_days_rest.append(away_days_off.days)
        home_team_series = df.iloc[team_index_current.get(home_team)]
        away_team_series = df.iloc[team_index_current.get(away_team)]
        stats = pd.concat([home_team_series, away_team_series])
        stats['Days-Rest-Home'] = home_days_off.days
        stats['Days-Rest-Away'] = away_days_off.days
        match_data.append(stats)

    games_data_frame = pd.concat(match_data, ignore_index=True, axis=1)
    games_data_frame = games_data_frame.T

    frame_ml = games_data_frame.drop(columns=['TEAM_ID', 'TEAM_NAME'])
    data = frame_ml.values
    data = data.astype(float)

    return data, todays_games_uo, frame_ml, home_team_odds, away_team_odds


def main():
    odds = None
    if args.odds:
        odds = SbrOddsProvider(sportsbook=args.odds).get_odds()
        games = create_todays_games_from_odds(odds)
        if len(games) == 0:
            print("No games found.")
            return
        if((games[0][0]+':'+games[0][1]) not in list(odds.keys())):
            print(games[0][0]+':'+games[0][1])
            print(Fore.RED, "--------------Games list not up to date for todays games!!! Scraping disabled until list is updated.--------------")
            print(Style.RESET_ALL)
            odds = None
        else:
            print(f"------------------{args.odds} odds data------------------")
            for g in odds.keys():
                home_team, away_team = g.split(":")
                print(f"{away_team} ({odds[g][away_team]['money_line_odds']}) @ {home_team} ({odds[g][home_team]['money_line_odds']})")
    else:
        data = get_todays_games_json(todays_games_url)
        games = create_todays_games(data)
    data = get_json_data(data_url)
    df = to_data_frame(data)
    data, todays_games_uo, frame_ml, home_team_odds, away_team_odds = createTodaysGames(games, df, odds)
    if args.nn:
        print("------------Neural Network Model Predictions-----------")
        data = tf.keras.utils.normalize(data, axis=1)
        NN_Runner.nn_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds)
        print("-------------------------------------------------------")
    if args.xgb:
        print("---------------XGBoost Model Predictions---------------")
        XGBoost_Runner.xgb_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds)
        print("-------------------------------------------------------")
    if args.A:
        print("---------------XGBoost Model Predictions---------------")
        XGBoost_Runner.xgb_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds)
        print("-------------------------------------------------------")
        data = tf.keras.utils.normalize(data, axis=1)
        print("------------Neural Network Model Predictions-----------")
        NN_Runner.nn_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds)
        print("-------------------------------------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Model to Run')
    parser.add_argument('-xgb', action='store_true', help='Run with XGBoost Model')
    parser.add_argument('-nn', action='store_true', help='Run with Neural Network Model')
    parser.add_argument('-A', action='store_true', help='Run all Models')
    parser.add_argument('-odds', help='Sportsbook to fetch from. (fanduel, draftkings, betmgm, pointsbet, caesars, wynn, bet_rivers_ny')
    args = parser.parse_args()
    main()
