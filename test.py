url_string = "[https://mementoserver-hrd.appspot.com/blob/get?uid%3D4571580492939264%26lib%3Dbase64V2hKKXlFKFFqSS1Ya0FMWDtNJjU%253D]"

# Strip the square brackets and split by comma (if there are multiple items)
url_list = url_string.strip("[]").split(", ")[0]

print(url_list)
