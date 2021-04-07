# curl 'https://trends.google.com/trends/api/widgetdata/relatedsearches?hl=en-US&tz=240&req=%7B%22restriction%22:%7B%22geo%22:%7B%22country%22:%22US%22%7D,%22time%22:%222020-01-01+2020-01-01%22,%22originalTimeRangeForExploreUrl%22:%222020-01-01+2020-01-01%22%7D,%22keywordType%22:%22QUERY%22,%22metric%22:%5B%22TOP%22,%22RISING%22%5D,%22trendinessSettings%22:%7B%22compareTime%22:%222019-12-31+2019-12-31%22%7D,%22requestOptions%22:%7B%22property%22:%22%22,%22backend%22:%22IZG%22,%22category%22:0%7D,%22language%22:%22en%22,%22userCountryCode%22:%22US%22%7D&token=APP6_UEAAAAAYGY3_8sVbBvDnQr5EvQeXP7go1RSCkVc' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Connection: keep-alive' -H 'Referer: https://trends.google.com/trends/explore?date=2020-01-01%202020-01-01&geo=US' -H 'Cookie: __utma=10102256.1078349782.1615785088.1615785088.1615785088.1; __utmz=10102256.1615785088.1.1.utmcsr=knowyourmeme.com|utmccn=(referral)|utmcmd=referral|utmcct=/memes/subcultures/undertale; __utmc=10102256; 1P_JAR=2021-03-31-20; NID=212=RmLqxIn0htEZlS4gqrxzLVebKRMW4as8tYpe7MOtDcMxehejRACx9MS1MtwyjfAH7QY9RGDLreCKr51Jnu_Gx1gVPoHt2kQT-HgZfYR9P2D_u5IhXV530acF0rYXEf4Sxzl6zbp2Fuja_Qez7fmp-yFHSX61NMjqTKqdAVYcbAZ8VYwLbKWf0QQJcCHzdJeRufCpWePURb7esdQr3BJUXpBsvSycABKbh8sAM2fUgcZ5qOAHzpaEGvFOhg; ANID=AHWqTUlW06RtE6PlB4g-ldi3_D12VapC8vlcZ4yyehfNonOlPqsHKI1CdVbH7-XD; SID=7gfRPnKhFUm-xablTnf90QEXBplzcGHTa4rhe-iFJw8wuA2mPk22ehaZoj-9NFIHQetr2w.; __Secure-3PSID=7gfRPnKhFUm-xablTnf90QEXBplzcGHTa4rhe-iFJw8wuA2mIjD5KYn410S2tdL699MKag.; HSID=AWVqnoXSu-WZVIAF9; SSID=AVfgr3swCux3hB6CI; APISID=TXJOTthRmPLweQ4q/AVJpYBgooLLLDVz5r; SAPISID=1yE4tX1J1fnVnQOl/A8TuTfh8LGQDx7BAV; __Secure-3PAPISID=1yE4tX1J1fnVnQOl/A8TuTfh8LGQDx7BAV; SIDCC=AJi4QfFF60OYJu36g8r_tpPRARFz5Q_M9LQdv3fFDf5MbYSTXbWwQMbvZdR-UlQ9co9FtZjgEID0; __Secure-3PSIDCC=AJi4QfFZOY53Zguf9EreJPzYoLTsBuEeP-2GWf_rHZGVpJvQPUtjeWwHCREy1wBe9GygwPqR6uA2; SEARCH_SAMESITE=CgQInZIB; CONSENT=YES+DE.en+V9+BX; OGPC=19022519-1:19022552-1:19023338-1:; S=billing-ui-v3=wrhpmkQTgkr1R7ava-wxmyEfExkT4Rll:billing-ui-v3-efe=wrhpmkQTgkr1R7ava-wxmyEfExkT4Rll' -H 'TE: Trailers'

# https://trends.google.com/trends/api/widgetdata/relatedsearches?hl=en-US&tz=240&req=%7B%22restriction%22:%7B%22geo%22:%7B%22country%22:%22US%22%7D,%22time%22:%222020-01-01+2020-01-01%22,%22originalTimeRangeForExploreUrl%22:%222020-01-01+2020-01-01%22%7D,%22keywordType%22:%22QUERY%22,%22metric%22:%5B%22TOP%22,%22RISING%22%5D,%22trendinessSettings%22:%7B%22compareTime%22:%222019-12-31+2019-12-31%22%7D,%22requestOptions%22:%7B%22property%22:%22%22,%22backend%22:%22IZG%22,%22category%22:0%7D,%22language%22:%22en%22,%22userCountryCode%22:%22US%22%7D&token=APP6_UEAAAAAYGY3_8sVbBvDnQr5EvQeXP7go1RSCkVc


# relatedsearches
# hl=en-US
# tz=240
# req={
#     "restriction": {
#         "geo": {"country":"US"},
#         "time": "2020-01-01+2020-01-01",
#         "originalTimeRangeForExploreUrl": "2020-01-01+2020-01-01"
#     },
#     "keywordType":"QUERY",
#     "metric":["TOP","RISING"],
#     "trendinessSettings": {"compareTime":"2019-12-31+2019-12-31"},
#     "requestOptions": {"property":"","backend":"IZG","category":0},
#     "language":"en",
#     "userCountryCode":"US"
# }
# token=APP6_UEAAAAAYGY3_8sVbBvDnQr5EvQeXP7go1RSCkVc

# import urllib.request, json
import json
from datetime import datetime, timedelta
import time
from pytrends.request import TrendReq
import pandas as pd
import pickle

# url = "https://trends.google.com/trends/api/widgetdata/relatedsearches?hl=en-US&tz=240&req=%7B%22restriction%22:%7B%22geo%22:%7B%22country%22:%22US%22%7D,%22time%22:%22{0}+{0}%22,%22originalTimeRangeForExploreUrl%22:%22{0}+{0}%22%7D,%22keywordType%22:%22QUERY%22,%22metric%22:%5B%22TOP%22,%22RISING%22%5D,%22trendinessSettings%22:%7B%22compareTime%22:%22{1}+{1}%22%7D,%22requestOptions%22:%7B%22property%22:%22%22,%22backend%22:%22IZG%22,%22category%22:0%7D,%22language%22:%22en%22,%22userCountryCode%22:%22US%22%7D&token=APP6_UEAAAAAYGY3_8sVbBvDnQr5EvQeXP7go1RSCkVc"

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

