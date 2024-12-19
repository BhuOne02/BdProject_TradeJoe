from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from transformers import pipeline
import requests
import PyRSS2Gen
import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route('/rss-news-feed')
def rss_feed():
    # Check if a CORS proxy is enabled using a query parameter
    # tickers = request.args.get('ticker')
    # print(tickers)
    news = get_news()
    processed_news = process_news(news)
    
    use_proxy = request.args.get('use_proxy', 'false').lower() == 'true'

    # Modify the link dynamically based on the proxy requirement
    rss_items = [
        PyRSS2Gen.RSSItem(
            title=f"{item['ticker']} - {item['title']} - {item['sentiment']}",
            link=f"https://cors-proxy.example.com/{item['link']}" if use_proxy else item["link"],
            description=item["summary"],
            guid=PyRSS2Gen.Guid(item["link"]),
            pubDate=datetime.datetime.fromtimestamp(item["datetime"])
        )
        for item in processed_news
    ]

    rss = PyRSS2Gen.RSS2(
        title="Stock News with Sentiment",
        link="http://0.0.0.0:6789/rss-news-feed",
        description="Latest stock-related news with sentiment analysis.",
        lastBuildDate=datetime.datetime.now(),
        items=rss_items
    )

    return Response(rss.to_xml(), content_type="application/rss+xml")


def get_news():
    API_KEY = 'ctdrbk1r01qng9gf9rf0ctdrbk1r01qng9gf9rfg'
    tickers = ['AAPL', 'TSLA', 'AMZN', 'GOOG']
    news = {}
    for ticker in tickers:
        url = f'https://finnhub.io/api/v1/company-news?symbol={ticker}&from=2024-12-01&to=2024-12-14&token={API_KEY}'
        response = requests.get(url)
        news[ticker] = response.json()
    return news


def process_news(news):
    sentiment_model = pipeline('sentiment-analysis', model='yiyanghkust/finbert-tone', device="mps")
    processed_news = []

    for ticker in news.keys():
        count = 5
        for item in news[ticker]:
            count -= 1    
            sentiment = sentiment_model(item['summary'])
            item['sentiment'] = sentiment
            processed_news.append({
                "ticker": item['related'],
                "title": item['headline'],
                "summary": item['summary'],
                "sentiment": item['sentiment'][0]['label'],
                "score": item['sentiment'][0]['score'], 
                "link": item['url'],
                "datetime": item['datetime'] 
            })
            if count == 0:
                break
    
    return processed_news


if __name__ == '__main__':
    app.run(debug=True, port=6789, host='0.0.0.0')
