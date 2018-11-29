from flask import Flask, redirect, render_template, request, url_for
import jsonapi_requests
import datetime as dt
import pytz

app = Flask(__name__)
FMT = '%H:%M:%S'
timezone = pytz.timezone("America/New_York")

# Get the current local time in Framingham time zone
def now_local_time():
    global timezone

    now = dt.datetime.now()
    now_tz_aware = timezone.localize(now)
    time_tz_aware_formatted = now_tz_aware.astimezone(timezone)
    return time_tz_aware_formatted

# Convert a crossing time to minutes till next train
def convert_crossing_time(crossing_time):
    global FMT
    global timezone

    # Convert string to datetime that is naive of time zone
    crossing_time_naive = dt.datetime.strptime(crossing_time, FMT)

    # Inefficient way to strip out timezone offset, surely there's a more Pythonic way.
    now_str = now_local_time().strftime(FMT)
    now_naive = dt.datetime.strptime(now_str, FMT)

    tdelta = crossing_time_naive - now_naive
    mins_till_next_crossing = int(tdelta.seconds/60) #-1140

    # Convert string to datetime
    # crossing_time_datetime = dt.datetime.strptime(crossing_time, FMT)

    # Add EST time zone, so I can do substraction on it with another time-zone aware datetime (now)
    # crossing_time_tz_aware = timezone.localize(crossing_time_datetime)
    # crossing_time_tz_aware_formatted = crossing_time_tz_aware.astimezone(timezone)

    # Convert crossing time to minutes from now.
    # now_formatted = now_local_time()
    # tdelta = crossing_time_tz_aware_formatted - now_formatted

    # 1200 was a Temporary fudge factor for AWS deployment.
    # 1140 is placeholder for now...hmmm...
    # mins_till_next_crossing = int(tdelta.seconds/60)
    return mins_till_next_crossing, crossing_time_naive


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
    crossing_times_debug = []

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
        mins_till_next_crossing, crossing_time_naive = convert_crossing_time(crossing_time)

        upcoming_crossings.append(mins_till_next_crossing)
        crossing_times_debug.append(crossing_time_naive)

    # Sort the times in ascending order. I noticed sometimes the MBTA API returns predictions out of order.
    upcoming_crossings.sort()

    # Add "minutes" string, using a list comprehension
    result = [str(crossing) + ' minutes' for crossing in upcoming_crossings]

    return result, crossing_times_debug


# Flask app

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":

        now_str = now_local_time().strftime(FMT)
        current_time = dt.datetime.strptime(now_str, FMT)

        upcoming_crossings, crossing_times_debug = next_crossings()

        return render_template("main_page.html", upcoming_trains=upcoming_crossings, current_time = current_time, crossing_times_debug=crossing_times_debug)

if __name__ == "__main__":
    app.run()