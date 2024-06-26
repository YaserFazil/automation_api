if (entry().field("Manual Entry")) {
    var title = entry().field("Title");
    message(title);
    var query = encodeURIComponent(title);
    var requestUrl = "http://127.0.0.1:5000/search-products?title=" + query;
    var options = {
        headers: {
            "api-key": "d9136037-f10e-4640-90db-e62d5c4d0ae3"
        }
    };
    var result = http().get(requestUrl, options);

    if (result.code == 200) {
        var data = JSON.parse(result.body);
        if (data.results && data.results.length > 0) {
            for (var i = 0; i < data.results.length && i < 10; i++) {
                var imageUrl = data.results[i].image;
                var cleanedImageUrl = imageUrl.replace(/,.*?(\.jpg)/, '$1'); // Optional: Adjust if necessary
                var fieldName = "Online Image " + (i + 1);
                entry().set(fieldName, cleanedImageUrl);
            }
        }
    }
    log(entry().field("Manual Entry"));
}
