"""
Midland Central Appraisal District Scraper v1.0

Operation:
    • Prompted to enter a single property to look up, otherwise it will loop the csv file in root
    containing the urls.
****• Need to change the neighborhood variable to your neighborhood

Output:
    Example:
                                ___________
        R000050656,2017,$218100            |
        R000050656,2016,$203360            |
        R000050656,2015,$203360            |--------- Change in valuation over last four years
        R000050656,2014,$196080            |          --- Property ID, Valuation Year, Valuation Amount
                                ___________|
                                      _____
        R000050656,RESIDENCE,1962,2232     |
        R000050656,GARAGE,1962,504         |
        R000050656,STG BLDG,2012,160       |--- Types of improvements
        R000050656,GLASS PORCH,1997,490    |    --- date associated with RESIDENCE is the construction date
                                      _____|    --- Property ID, Improvement Type, Improvement Year, Improvement Sqft

        R000050656,$3,713.82 ------------------ Total Assessed Tax for current year
                                                --- Property ID, Tax Assessed
Analysis:
    Use your preferred tool

Future Versions:
    • get list of neighborhoods, scrape all properties, eliminate duplicates (if any)
         • Didn't mess with, but would be easy to scrape a neighborhood
                • link is:
                    http://iswdataclient.azurewebsites.net/webSearchLegal.aspx?dbkey=midlandcad&stype=legal&sdata=NEIGHBORHOOD_NAME#top
                • just replace neighborhood name with your neighborhood and you could fetch the results with
                    BeautifulSoup (<a id="ucResultsGrid_)
            • Before I started this I had already copy and pasted the 700 or so homes in my neighborhood to excel
                • So as of now, it depends on a csv in root containing the urls
                    • or just the property ids and you can prepend:
                        http://iswdataclient.azurewebsites.net/webProperty.aspx?dbkey=midlandcad&stype=legal&sdata=NEIGHBORHOOD_NAME&id=
"""

import requests
import urllib
from bs4 import BeautifulSoup
import csv
import numpy as np

valuation_headers = ['property_id', 'year', 'valuation']
improvements_headers = ['property_id', 'improvement', 'year', 'sqft']
taxes_headers = ['property_id', 'tax']
# change this to your neighborhood -- if no results, make sure MCAD website has the same spelling
neighborhood = "WEDGEWOOD PARK"
neighborhood = neighborhood.replace(" ", "%20")
url = "http://iswdataclient.azurewebsites.net/webProperty.aspx?dbkey=midlandcad&stype=legal&sdata={}&id=".format(
    neighborhood)


def choice():
    property_id = input("Enter a Property ID or type anything else to loop:")
    if property_id != "":
        if len(property_id.strip()) != 10 and property_id[0].strip() != "R":
            print("Running Loop!")
            loop_csv()
        elif len(property_id.strip()) == 10 and property_id[0].strip().capitalize() == "R":
            print(neighborhood)
            property_id = property_id.strip().capitalize()
            print("Looking up property: {} in {}".format(property_id, neighborhood.replace("%20", " ")))
            try:
                single_lookup(property_id)
            except:
                write_error(property_id, 'lookup error')
            choice()


def single_lookup(property_id):
    create_files()
    valuation = []
    improvements = []
    taxes = []
    str_url = "{}{}".format(url, property_id)
    html_txt = urllib.request.urlopen(str_url)
    bs = BeautifulSoup(html_txt, "lxml")
    try:
        valuation = get_valuation(bs)
    except:
        write_error(property_id, 'valuation error')
    try:
        improvements = get_improvements(bs)
    except:
        write_error(property_id, 'improvements error')
    try:
        taxes = get_taxes(bs)
    except:
        write_error(property_id, 'taxes error')
    entries = assemble_entries(valuation, improvements, taxes, property_id)


def create_files():
    # create each txt file for output and input headers
    with open('valuation.txt', 'w') as outfile:
        for item in valuation_headers:
            outfile.write("{},".format(item))
    with open('improvements.txt', 'w') as outfile:
        for item in improvements_headers:
            outfile.write("{},".format(item))
    with open('taxes.txt', 'w') as outfile:
        for item in taxes_headers:
            outfile.write("{},".format(item))


def write_error(property_id, error_type):
    with open('errors.txt', 'a', newline='') as outfile:
        outfile.write("{}{}\n".format(property_id, error_type))


def loop_csv():
    # create output files
    create_files()
    # open csv containing urls for all of the homes in my neighborhood
    with open('urls.csv', 'r') as infile:
        # create an iterable reader object from the csv file
        reader = csv.reader(infile)
        # setup lists (arrays)
        valuation = []
        improvements = []
        taxes = []
        # loop through each row of the file
        for row in reader:
            # was having trouble with url encoding ':' in 'http:' incorrectly, converted to str to be sure
            # other ways to do this, I'm sure
            str_url = ''.join(row)
            # get just the last 10 digits of the url for the property_id
            property_id = str_url[-10:]
            # get all of the html from the url
            html_txt = urllib.request.urlopen(str_url)
            # create a beautifulsoup object -- great for getting info out of html
            bs = BeautifulSoup(html_txt, "lxml")
            # get valuation information
            try:
                valuation = get_valuation(bs)
            except:
                write_error(property_id, 'valuation error')
            # get improvements information
            try:
                improvements = get_improvements(bs)
            except:
                write_error(property_id, 'improvements error')
            # get taxes information
            try:
                taxes = get_taxes(bs)
            except:
                write_error(property_id, 'taxes error')
            # Format for output
            entries = assemble_entries(valuation, improvements, taxes, property_id)
            str_url = ""


def get_valuation(soup):
    # pulls html for the selected criteria, summary='Valuation Table'
    valuation = soup.find(lambda tag: tag.has_attr('summary') and tag['summary'] == "Valuation Table").get_text()
    # split the result into lines
    valuation_lines = valuation.splitlines()
    # header information is fixed
    header = valuation_lines[5:9]
    # assessed value is fixed
    assessed = valuation_lines[97:101]
    # use numpy to concatenate the two arrays vertically
    valuation = np.vstack((header, assessed))
    return valuation


def get_improvements(soup):
    # setup lists (arrays)
    # there are probably better ways to do this portion, but still learning BeautifulSoup
    arr_improvements = []
    arr_improvements_year = []
    arr_improvements_sqft = []
    # find the table with the information regarding improvements
    improvements = soup.find(lambda tag: tag.has_attr('summary') and tag['summary'] == "Building Details")
    # get the table rows
    improvement_data = improvements.findAll("tr")
    # if you want to loop and include an index without having to increment, you can use enumerate()
    for i, item in enumerate(improvement_data):
        # find the table cells -- always in the same format
        for j, td in enumerate(item.findAll("td")):
            # improvement type - text=True strips out all of the html elements
            if j == 2:
                arr_improvements.append(td.findAll(text=True))
            # improvement year
            elif j == 3:
                arr_improvements_year.append(td.findAll(text=True))
            # improvement sqft
            elif j == 4:
                arr_improvements_sqft.append(td.findAll(text=True))
    # this step isn't really necessary, could probably be removed
    improvements = arr_improvements
    years = arr_improvements_year
    sqft = arr_improvements_sqft
    # use numpy to concatenate the 3 lists horizontally
    improvements = np.hstack((improvements, years, sqft))
    return improvements


def get_taxes(soup):
    # setup tax list
    tax_items = []
    # find the associated table
    taxes = soup.find(lambda tag: tag.has_attr('summary') and tag['summary'] == "Estimated Taxes")
    # only need the summary row (which is always bold)
    for strong_tag in taxes.findAll("strong"):
        tax_items.append(strong_tag.text)
    # just get the last value, which is the total assessed tax
    return (tax_items[-1])


def assemble_entries(val, imprv, tax, property_id):
    # the values were still being treated as numpy arrays, so I couldn't remove the commas in the
    # variables that were currency, but creating a new variable allowed me to replace the commas,
    # tried to create the variables dynamically in a loop, but it wasn't working properly
    val1 = val[1][0]
    val2 = val[1][1]
    val3 = val[1][2]
    val4 = val[1][3]
    """
    for x in range(0, 4):
        y = x
        y += 1
        exec("val{} = val[1,{}]".format(y, x))
    """
    """
    there are always four lines, one for each year
    should look like: R000050406,2017,$123930
                      R000050406,2016,$118910
                      R000050406,2015,$114220
                      R000050406,2014,$103840
    """
    valuation_lines = "\n{},{},{}\n{},{},{}\n{},{},{}\n{},{},{}".format(property_id, val[0][0], val1.replace(",", ""),
                                                                        property_id, val[0][1], val2.replace(",", ""),
                                                                        property_id, val[0][2], val3.replace(",", ""),
                                                                        property_id, val[0][3], val4.replace(",", ""))
    print(valuation_lines)
    # write to file
    with open("valuation.txt", 'a', newline='') as outfile:
        outfile.write(valuation_lines)

    # the number of improvements can vary, but .shape can tell me the dimensions of the array
    # and allow me to iterate over it accordingly
    """
    should look like:R000050407,RESIDENCE,1959,1612
                     R000050407,GARAGE,1959,483
                     R000050407,ADDITION,1959,360
    """
    improvement_lines = []
    x = 0
    while x < imprv.shape[0]:
        sqft = imprv[x][2]
        sqft = sqft.replace(",", "")
        # presentation view
        # improvement_lines.append("{} ({}) - {}sqft".format(imprv[x][0].capitalize(), imprv[x][1], sqft))
        # csv view
        improvement_lines.append("{},{},{},{}".format(property_id, imprv[x][0], imprv[x][1], sqft))
        x += 1

    improvement_lines = "\n".join(improvement_lines)
    print(improvement_lines)
    # write to file
    with open("improvements.txt", 'a', newline='') as outfile:
        outfile.write('\n{}.'.format(improvement_lines))

    # not much extra formatting required for taxes
    """
    should look like: R000050407,$3,192.19
    """
    print("{},{}".format(property_id, tax))
    with open("taxes.txt", 'a', newline='') as outfile:
        outfile.write("\n{},{}".format(property_id, tax))


def main():
    choice()


if __name__ == '__main__':
    main()
