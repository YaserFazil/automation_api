import requests
import json
import time
import math
import hashlib

SEARCH_BARCODE_HEADERS = {
    "User-Agent": "okhttp/4.9.1",
}




def gen_authtoken(timestamp, country):
    secret = "5b6874d3a20417591bd5464a25a37bc6" if country == "US" else "efb8826e4544bbab8992d757ec8b1116"
    username = "amzn-mbl-cscan-us" if country == "US" else "amzn-mbl-cscan-ca"
    application = "amzn-mbl-cscan-us" if country == "US" else "amzn-mbl-cscan-ca"
    sha512_hash = hashlib.sha512()
    data = secret + username + application + str(timestamp)
    sha512_hash.update(data.encode())

    return sha512_hash.hexdigest().upper()


def search_barcode_logic(barcode, country="CA"):
    search_barcode_endpoint = "https://match-visualsearch.amazon.com/vsearch/2.0" if country == "US" else "https://match-visualsearch-ca.amazon.com/vsearch/2.0"
    timestamp = math.floor(time.time())
    authtoken = gen_authtoken(timestamp, country)
    print(authtoken)

    body_params = {
        "clientMessageVersion": "1.0",
        "orientation": "90",
        "uiMode": "barcode_scanner",
        "application": "amzn-mbl-cscan-us" if country == "US" else "amzn-mbl-cscan-ca",
        "lang": "en_US" if country == "US" else "en_CA",
        "ts": timestamp,
        "username": "amzn-mbl-cscan-us" if country == "US" else "amzn-mbl-cscan-ca",
        "groupingId": "5045eb49-d8bb-4cc5-ad5e-6796e894b876",
        "query_metadata": "",
        "vsearch_params_json": "",
        "authtoken": authtoken,
    }

    query_metdata = {
        "amznSessionId": "135-7799391-5389824",
        "clientVersion": "28.16.0.100",
        "cardsVersion": "1.0",
        "clientMessageVersion": "1.0",
        "amznDirectedCustomerId": "",
        "clientDeviceId": "06820589-f27d-40a0-ac10-b837d8b231ff",  # changes
        "clientDevice": "Android - TECNO KF6i",  # changes
        "deviceManufacturer": "TECNO MOBILE",  # changes
        "clientDeviceVersion": "11",
        "intentScore": "6.000000",
        "clientId": "616076d7-be9c-4274-a566-ca80ddf70946",  # changes
        "intentId": "0",
        "initialPayloadSize": "0",
        "version": "0.9",
        "extra": "0",
    }

    vsearch_params_json = {
        "occipital": {"params": {"barcode": barcode, "barcodeType": "CODE_128"}}
    }

    body_params["query_metadata"] = json.dumps(query_metdata)
    body_params["vsearch_params_json"] = json.dumps(vsearch_params_json)

    res = requests.post(
        search_barcode_endpoint, headers=SEARCH_BARCODE_HEADERS, data=body_params
    )

    if res.ok:
        response = res.json()
        print(response)
        if (
            "occipital" in response
            and "searchResult" in response["occipital"]
            and response["occipital"]["searchResult"]
            and type(response["occipital"]["searchResult"]) == list
            and "properties" in response["occipital"]["searchResult"][0]
            and "convertedBarcodes"
            in response["occipital"]["searchResult"][0]["properties"]
            and response["occipital"]["searchResult"][0]["properties"][
                "convertedBarcodes"
            ]
        ):
            converted_barcode = res.json()["occipital"]["searchResult"][0][
                "properties"
            ]["convertedBarcodes"][0]
            print(f"Converted barcode : {converted_barcode}")

            return converted_barcode
    else:
        print(res.status_code)
        print(res.text)

    return None


def search_barcode(barcode):
    country = "CA"
    asin = search_barcode_logic(barcode, country)
    if not asin:
        country = "US"
        asin = search_barcode_logic(barcode, country)
    if asin:
        return {"status": "success", "code": asin, "country": country}
    else:
        return {"status": "failed", "msg": "Not found ASIN"}
search_barcode("X002OKP889")