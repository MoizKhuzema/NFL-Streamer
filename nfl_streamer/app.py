import re
import requests
from bs4 import BeautifulSoup
from langchain.document_loaders import UnstructuredURLLoader
from flask import Flask, render_template, request
from concurrent.futures import ThreadPoolExecutor


app = Flask(__name__)


def extract_event_urls(url):
  # Send a GET request to the URL
  response = requests.get(url)
  # Check if the request was successful (status code 200)
  if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
  else:
    print(response.status_code)
    return None
  # Find all anchor tags with the specified format in the href attribute
  urls = [a['href'] for a in soup.find_all('a', href=lambda href: href and 'https://nflstreams.club/event/' in href)]
  return urls


def extract_video_link(url):
    # Send a GET request to the URL
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    try:
        # Extract the YouTube video URL from the iframe src attribute
        return soup.find('iframe')['src']
    except:
        return 'Links will appear around 60 mins prior to kick-off'


def extract_matches_schedule(url, league):
  # Load HTML
  loader = UnstructuredURLLoader([url])
  html = loader.load()
  data = re.sub(r'(\n\s*)+', '\n', html[0].page_content)

  if "There are no matches today" in data:
    return []

  # Regular expression pattern to match date, time, and team names
  pattern = re.compile(r'(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2} [APMapm]+)\n(.+?) vs (.+?)\nLink')
  matches = pattern.findall(data)

  # Get match links
  print('done 1')
  urls = extract_event_urls(url)
  print('done 2')
  with ThreadPoolExecutor() as executor:
        video_links = list(executor.map(extract_video_link, urls))
  print('done 3')
  match_list = []
  for i, match in enumerate(matches, start=1):
      date, time, team1, team2 = match
      match_list.append(
          {'league': league, 'home_team': team1, 'away_team': team2, 'date': date, 'time': time, 'stream_link': video_links[i-1]}
      )
  return match_list


@app.route('/')
def index():
    return render_template('index.html', data=extract_matches_schedule('https://nflstreams.club/schedule/week/nfl?week=0', 'nfl'))


@app.route('/update-content', methods=['GET'])
def update_content():
    selected_league = request.args.get('league', 'nfl')
    selected_week = request.args.get('week', 'this-week')

    if selected_week == 'this-week' and selected_league == 'nfl':
        url = 'https://nflstreams.club/schedule/week/nfl?week=0'
    elif selected_week == 'this-week' and selected_league == 'ncaa':
        url = 'https://nflstreams.club/schedule/week/ncaa-regular-season?week=0'
    elif selected_week == 'next-week' and selected_league == 'nfl':
        url = 'https://nflstreams.club/schedule/week/nfl?week=1'
    elif selected_week == 'next-week' and selected_league == 'ncaa':
        url = 'https://nflstreams.club/schedule/week/ncaa-regular-season?week=1'
    elif selected_week == 'last-week' and selected_league == 'nfl':
        url = 'https://nflstreams.club/schedule/week/nfl?week=-1'
    else:
        url = 'https://nflstreams.club/schedule/week/ncaa-regular-season?week=-1'

    data = extract_matches_schedule(url, selected_league)

    # Render the matches table template with the fetched data
    return render_template('matches_table.html', data=data)


if __name__ == '__main__':
    app.run(debug=True)
