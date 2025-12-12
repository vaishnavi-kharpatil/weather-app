from flask import Flask, request, jsonify
import requests, time

app = Flask(__name__)

API_KEY = "API_KEY"
URL = {
    "weather": "https://api.openweathermap.org/data/2.5/weather",
    "forecast": "https://api.openweathermap.org/data/2.5/forecast"
}
CACHE, TTL = {}, 300



# Generic fetcher + caching

def fetch(city, mode):
    key = f"{mode}:{city.lower()}"
    now = time.time()

    if key in CACHE and now - CACHE[key]["t"] < TTL:
        return CACHE[key]["data"], True

    try:
        r = requests.get(URL[mode], params={
            "q": city, "appid": API_KEY, "units": "metric"
        }, timeout=5)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise RuntimeError(str(e))

    CACHE[key] = {"t": now, "data": data}
    return data, False



# UI Home Page

@app.route("/", methods=["GET", "POST"])
def home():
    city = request.form.get("city", "Mumbai")

    try:
        data, cached = fetch(city, "weather")
        temp = data["main"]["temp"]
        country = data["sys"]["country"]
        lon, lat = data["coord"]["lon"], data["coord"]["lat"]
        pressure, humidity = data["main"]["pressure"], data["main"]["humidity"]
    except Exception as e:
        return f"<h3>Error: {e}</h3>"

    return f"""
    <html>
    <body style="font-family:Arial;background:#eef;padding:40px;">
        <form method="POST" style="text-align:center;">
            <input name="city" placeholder="Enter city" style="padding:10px;width:200px;">
            <button style="padding:10px;">Get Weather</button>
        </form>

        <div style="max-width:600px;margin:auto;background:white;padding:20px;border-radius:10px;">
            <h2 style="text-align:center;">Weather for {city}</h2>
            <table border="1" width="100%" style="border-collapse:collapse;">
                <tr><th>Country</th><th>Coords</th><th>Temp °C</th><th>Pressure</th><th>Humidity</th></tr>
                <tr>
                    <td>{country}</td>
                    <td>{lon}, {lat}</td>
                    <td>{temp}</td>
                    <td>{pressure}</td>
                    <td>{humidity}</td>
                </tr>
            </table>
        </div>
    </body>
    </html>
    """



# API: Current Weather (JSON)

@app.route("/weather")
def weather_api():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "city required"}), 400

    try:
        data, cached = fetch(city, "weather")
        temp = data["main"]["temp"]
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    return jsonify({
        "city": city,
        "cached": cached,
        "temp": temp,
        "country": data["sys"]["country"],
        "coord": data["coord"]
    })



# API: Forecast List

@app.route("/forecast")
def forecast_list():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "city required"}), 400

    min_t = request.args.get("min_temp", type=float)
    max_t = request.args.get("max_temp", type=float)
    limit = request.args.get("limit", type=int)

    try:
        data, cached = fetch(city, "forecast")
        items = data["list"]
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    result = []
    for i, item in enumerate(items):
        temp = item["main"]["temp"]
        if min_t and temp < min_t: continue
        if max_t and temp > max_t: continue

        result.append({
            "id": i,
            "time": item.get("dt_txt", ""),
            "temp": temp,
            "desc": item["weather"][0]["description"]
        })

    if limit:
        result = result[:limit]

    return jsonify({"city": city, "cached": cached, "count": len(result), "items": result})


# API: Forecast Detail
@app.route("/forecast/<city>/<int:item_id>")
def forecast_detail(city, item_id):
    try:
        data, cached = fetch(city, "forecast")
        item = data["list"][item_id]
    except IndexError:
        return jsonify({"error": "invalid item_id"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    return jsonify({
        "city": city,
        "cached": cached,
        "id": item_id,
        "time": item.get("dt_txt", ""),
        "temp": item["main"]["temp"],
        "desc": item["weather"][0]["description"],
        "raw": item
    })


if __name__ == "__main__":
    app.run(debug=True)