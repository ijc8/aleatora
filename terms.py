import json
from datetime import datetime, timedelta
import time
from pytrends.request import TrendReq
import pandas as pd
import pickle

# Modified subclass of pytrends to suit my needs (getting top terms on a day without specifying queries).
class MyTrendReq(TrendReq):
    def related_queries(self):
        """Request data from Google's Related Queries section and return a dictionary of dataframes
        If no top and/or rising related queries are found, the value for the key "top" and/or "rising" will be None
        """
        # make the request
        related_payload = dict()
        result_dict = dict()
        for request_json in self.related_queries_widget_list:
            # ensure we know which keyword we are looking at rather than relying on order
            if 'complexKeywordsRestriction' in request_json['request']['restriction']:
                kw = request_json['request']['restriction'][
                    'complexKeywordsRestriction']['keyword'][0]['value']
            else:
                kw = ''
            # convert to string as requests will mangle
            related_payload['req'] = json.dumps(request_json['request'])
            related_payload['token'] = request_json['token']
            related_payload['tz'] = self.tz
            # parse the returned json
            req_json = self._get_data(
                url=TrendReq.RELATED_QUERIES_URL,
                method=TrendReq.GET_METHOD,
                trim_chars=5,
                params=related_payload,
            )
            # top queries
            try:
                top_df = pd.DataFrame(
                    req_json['default']['rankedList'][0]['rankedKeyword'])
                top_df = top_df[['query', 'value']]
            except KeyError:
                # in case no top queries are found, the lines above will throw a KeyError
                top_df = None

            # rising queries
            try:
                rising_df = pd.DataFrame(
                    req_json['default']['rankedList'][1]['rankedKeyword'])
                rising_df = rising_df[['query', 'value']]
            except KeyError:
                # in case no rising queries are found, the lines above will throw a KeyError
                rising_df = None

            result_dict[kw] = {'top': top_df, 'rising': rising_df}
        return result_dict

pytrends = MyTrendReq(hl='en-US', geo='US')

start_date = datetime(2020, 1, 1)
end_date = datetime(2021, 1, 1)
for i in range((end_date - start_date).days + 1):
    today = (start_date + timedelta(i)).strftime('%Y-%m-%d')
    print(today)
    pytrends.build_payload([''], timeframe=f'{today} {today}')
    result = pytrends.related_queries()
    print(result)
    with open(f'trends/{today}.pkl', 'wb') as f:
        pickle.dump(result, f)
    time.sleep(1)

