from flask import Flask, render_template, request, redirect
import sqlite3
import requests

app = Flask(__name__)
API_KEY = 'BP8GPRYV53UQ56SHJR5EFCJ77'

# Matches weather condition keywords to a relevant icon filename
def get_icon_filename(condition):
    condition = condition.lower()
    if "clear" in condition:
        return "clear-day.png"
    elif "partly cloudy" in condition:
        return "partly-cloudy-day.png"
    elif "cloud" in condition:
        return "overcast.png"
    elif "rain" in condition:
        return "rain.png"
    elif "snow" in condition:
        return "snow.png"
    elif "thunder" in condition:
        return "thunder.png"
    else:
        return "unknown.png"

# Retrieves weather data for the given city from the Visual Crossing API
def get_weather(city):
    url = f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/weatherdata/forecast?aggregateHours=24&contentType=json&unitGroup=metric&locationMode=single&key={API_KEY}&locations={city}'
    response = requests.get(url)
    data = response.json()

    # If the API response doesn’t contain weather info, exit early
    if 'location' not in data:
        return None

    current = data['location'].get('currentConditions', {})
    fallback = data['location'].get('values', [{}])[0]
    condition = current.get('conditions') or fallback.get('conditions', 'Unavailable')

    return {
        'city': city,
        'temperature': current.get('temp', 'N/A'),
        'condition': condition,
        'icon': get_icon_filename(condition)
    }

# Main route – displays weather cards and handles form submissions
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = sqlite3.connect('data/weather.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT UNIQUE,
        temperature REAL,
        condition TEXT,
        icon TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    message = None           # Message text to display
    message_type = None      # Bulma class: 'is-success' or 'is-danger'

    if request.method == 'POST':
        city = request.form['city']
        weather = get_weather(city)

        if weather:
            try:
                c.execute("INSERT INTO cities (city, temperature, condition, icon) VALUES (?, ?, ?, ?)",
                     (weather['city'], weather['temperature'], weather['condition'], weather['icon']))
                conn.commit()
                message = f"{weather['city']} added successfully."
                message_type = "is-success"
            except sqlite3.IntegrityError:
                message = f"{city} is already in the list."
                message_type = "is-danger"
        else:
            message = f"Could not retrieve weather data for '{city}'."
            message_type = "is-danger"

    c.execute("SELECT * FROM cities")
    cities = c.fetchall()
    conn.close()

    # Display latest city added in the scrolling marquee
    marquee_message = ""
    if cities:
        latest = cities[-1]
        marquee_message = f"Latest: {latest[0]} — {latest[1]}°C, {latest[2]}"

    return render_template('index.html',
                           cities=cities,
                           marquee_message=marquee_message,
                           message=message,
                           message_type=message_type)

# Handles deletion of a city card when "X" is clicked
@app.route('/delete/<city>', methods=['POST'])
def delete_city(city):
    conn = sqlite3.connect('data/weather.db')
    c = conn.cursor()
    c.execute("DELETE FROM cities WHERE city=?", (city,))
    conn.commit()
    conn.close()
    return redirect('/')

# Runs the Flask server locally
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
