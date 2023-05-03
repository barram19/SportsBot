!pip install requests


# Set API endpoint URL and API key

url = 'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey=8f283a0b9aa2f6e2b517c77b786bb1cb&bookmakers=fanduel&markets=h2h,spreads,totals&oddsFormat=american'
api_key = '8f283a0b9aa2f6e2b517c77b786bb1cb'


# Set headers for the request
headers = {
    'Content-Type': 'application/json',
    'x-api-key': api_key,
}

# Make the request and get the response data
response = requests.get(url, params=parameters, headers=headers)
data = response.json()
print(data[0]) # Access the first element of the list
mlb_odds = (data[0])
