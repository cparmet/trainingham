from flask import Flask, redirect, render_template, request, url_for
import jsonapi_requests
import datetime as dt
import pytz

app = Flask(__name__)
FMT = '%H:%M:%S'

# Get the current local time in Framingham time zone
def now_local_time():
    global FMT

    now = dt.datetime.now()
    timezone = pytz.timezone("America/New_York")
    now_tz_aware = timezone.localize(now)
    time_tz_aware = dt.time(hour=now_tz_aware.hour, minute=now_tz_aware.minute)
    time_tz_aware_formatted = dt.datetime.strptime(time_tz_aware.strftime(FMT), FMT)
    return time_tz_aware_formatted


# Convert a crossing time to minutes till next train
def convert_crossing_time(crossing_time):
    global FMT

    crossing_time_formatted = dt.datetime.strptime(crossing_time, FMT)
    now_formatted = now_local_time()
    tdelta = crossing_time_formatted - now_formatted
    # 1200 is a Temporary fudge factor. Needs a permanent fix.
    mins_till_next_crossing = int(tdelta.seconds / 60) - 1200
    return mins_till_next_crossing


# Get the predictions for next train crossing times, as many as MBTA is predicting.
def next_crossings():

    # Use MBTA API to get upcoming train crossings
    api = jsonapi_requests.Api.config({
        'API_ROOT': 'https://api-v3.mbta.com/',
        #     'AUTH': ('basic_auth_login', 'basic_auth_password'),
        'VALIDATE_SSL': False,
        'TIMEOUT': 1,
    })

    endpoint = api.endpoint('predictions?filter[stop]=Framingham&filter[route]=CR-Worcester&page[offset]=0&page[limit]=3')
    response = endpoint.get()

    upcoming_crossings = []

    # No trains predicted?
    if not len(response.data):
        return ['No imminent trains predicted by MBTA.']

    for i, r in enumerate(response.data):
        direction = str(['outbound' if r.attributes['direction_id'] == 1 else 'inbound'][0])

        # For an inbound train, the next time it will depart from Framingham
        # For an outbound train, we'd want to use arrival time.
        if direction == 'inbound':
            try:
                _, crossing_time = r.attributes['departure_time'].split('T')
            except:
                # If there's no departure time, it's not useful to me. Don't add a train prediction.
                # Maybe we have an inbound train arriving at Framingham and going no further?
                continue
        else:
            try:
                _, crossing_time = r.attributes['arrival_time'].split('T')
            except:
                # If there's no arrival time, it's not useful to me. Don't add a train prediction.
                # I don't know why an inbound train predicted for Framingham wouldn't arrive there.
                # But hey, strange things happen on the rails.
                continue

        crossing_time, _ = crossing_time.split('-')
        mins_till_next_crossing = convert_crossing_time(crossing_time)
        upcoming_crossings.append(str(mins_till_next_crossing) + ' minutes')

    return upcoming_crossings


# Flask app

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":

        upcoming_crossings = next_crossings()

        return render_template("main_page.html", upcoming_trains=upcoming_crossings)

if __name__ == "__main__":
    app.run()