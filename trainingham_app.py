from flask import Flask, redirect, render_template, request, url_for
import jsonapi_requests
import datetime as dt
import dateutil.parser
import pytz

app = Flask(__name__)

def convert_crossing_time(crossing_time):
    ''' Convert a crossing time to minutes from now till next train
    '''

    # What time is it now? Time-zone aware datetime.
    now_tzaware = dt.datetime.now(pytz.utc)

    # Use dateutil's sweet parser to convert time from MBTA API into a time-zone aware datetime.
    crossing_time_tzaware = dateutil.parser.parse(crossing_time)

    tdelta = crossing_time_tzaware  - now_tzaware

    # Convert to minutes till. Use // for floor division, rounds down. I'd rather be a little early.
    mins_till_next_crossing = int(tdelta.seconds // 60) #-1140

    return mins_till_next_crossing


def next_crossings():
    '''Get the predictions for next train crossing times, as many as MBTA is predicting.
    '''

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

    # We have trains!
    for i, r in enumerate(response.data):
        direction = str(['outbound' if r.attributes['direction_id'] == 1 else 'inbound'][0])

        # For an inbound train, the next time it will depart from Framingham.
        # For an outbound train, we'd want to use arrival time.
        if direction == 'inbound':
            try:
                # Don't split out (remove) today's date. Need it.
                # _, crossing_time = r.attributes['departure_time'].split('T')
                crossing_time = r.attributes['departure_time']
            except:
                # If there's no departure time, it's not useful to me. Don't add a train prediction.
                # Maybe we have an inbound train arriving at Framingham and going no further?
                continue
        else:
            try:
                # Don't split out (remove) today's date. Need it.
                # _, crossing_time = r.attributes['arrival_time'].split('T')
                crossing_time = r.attributes['arrival_time']
            except:
                # If there's no arrival time, it's not useful to me. Don't add a train prediction.
                # I don't know why an inbound train predicted for Framingham wouldn't arrive there.
                # But hey, strange things happen on the rails.
                continue

        # Use dateutil's parser to convert it to a full tz aware datetime, including timezone offset and today's date.
        mins_till_next_crossing = convert_crossing_time(crossing_time)

        if mins_till_next_crossing>=0:
            upcoming_crossings.append(mins_till_next_crossing)

    # Sort the times in ascending order. I noticed sometimes the MBTA API returns predictions out of order.
    upcoming_crossings.sort()

    # Add "minutes" string, using a list comprehension
    result = [str(crossing) + ' minutes' for crossing in upcoming_crossings]

    return result


# Flask app

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":

        upcoming_crossings = next_crossings()

        return render_template("main_page.html", upcoming_trains=upcoming_crossings)

if __name__ == "__main__":
    app.run()