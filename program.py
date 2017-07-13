"""
Midland Central Appraisal District Scraper v1.1

Operation:
    • Prompted to enter a a single property or use the street/neighborhood lookup

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

Version 1.1
    • Street Lookup - use 's:<street name>' to look up all the properties on that street
    • Neighborhood Lookup - use 'n:<neighborhood name>' to look up all the properties in that neighborhood

    • summary data will now be written to summary.txt
        ['property_id', 'geographic_id', 'owner_name', 'address', 'legal', 'market_value']

Version 1.0
    • Single property (by property code) or loop (from root csv) lookup

"""
import re
import requests
import urllib
from bs4 import BeautifulSoup
import csv
import numpy as np

valuation_headers = ['property_id', 'year', 'valuation']
improvements_headers = ['property_id', 'improvement', 'year', 'sqft']
taxes_headers = ['property_id', 'tax']
summary_headers = ['property_id', 'geographic_id', 'owner_name', 'address', 'legal', 'market_value']
# TODO: no longer applies, once the street/neighborhood is entered, will just be looking up properties
# change this to your neighborhood -- if no results, make sure MCAD website has the same spelling
base_url = "http://iswdataclient.azurewebsites.net/webProperty.aspx?dbkey=midlandcad&id="


def choice():
    create_files()
    property_id = input(
        "Enter a Property ID, street name (s:<name>), or neighborhood name (n:<name>):")
    if property_id != "":
        if len(property_id.strip()) == 10 and property_id[0].strip().capitalize() == "R":
            # print(neighborhood)
            property_id = property_id.strip().capitalize()
            print("Looking up property: {} in {}".format(property_id, neighborhood.replace("%20", " ")))
            try:
                single_lookup(property_id)
            except:
                write_error(property_id, 'lookup error')
            choice()
        elif 'n:' in property_id.strip() or 's:' in property_id.strip():
            fetch_properties(property_id)
        else:
            print("Unrecognized command")
            quit()


def fetch_properties(loc_type):
    if loc_type[0] == 's':
        stype = 'situs'
        location = loc_type.replace("s:", "").replace(" ", "%20")
        search_url = "http://iswdataclient.azurewebsites.net/webSearchAddress.aspx?dbkey=midlandcad&stype={}&sdata=".format(
            stype)
        search_url = "{}{}%7c0%7c".format(search_url, location)  # addition necessary when looking up street
    elif loc_type[0] == 'n':
        stype = 'legal'
        location = loc_type.replace("n:", "").replace(" ", "%20")
        search_url = "http://iswdataclient.azurewebsites.net/webSearchAddress.aspx?dbkey=midlandcad&stype={}&sdata={}".format(
            stype, location)

    form_data = {
        'ucSearchAddress_searchstreet': location,
    }

    data = urllib.parse.urlencode(form_data).encode("utf-8")
    req = urllib.request.Request(search_url)
    html_txt = urllib.request.urlopen(req, data=data)
    bs = BeautifulSoup(html_txt, "lxml")
    raw_data = create_raw_data(bs)
    property_ids = []
    property_data = []
    property_summary_data = [[]]
    for i, properties in enumerate(raw_data):
        if len(properties) != 0:
            if properties[0] == 'View Property':
                # print(i, properties)
                property_ids.append(properties[1])
                for x in range(1, len(properties) - 1):
                    property_data.append(properties[x])

                property_summary_data.append(property_data)
                with open("summary.txt", 'a', newline='') as outfile:
                    outfile.write("{},{},{},{},{},{}\n".format(property_data[0],
                                                               property_data[1],
                                                               property_data[2],
                                                               property_data[3],
                                                               property_data[4],
                                                               property_data[5]))

                property_data = []

    # print(property_summary_data)
    # print(len(property_ids))

    if len(property_ids) == 0:
        print("No properties found for '{}'.".format(location))
    else:
        print("Fetching information for properties...")
        get_metrics(property_ids, property_summary_data)
        # print("Properties: {}".format(property_ids))


def create_raw_data(soup):
    trs = soup.findAll('tr')

    property_info = [[]]
    indv_prop = []
    for i, tr in enumerate(trs):
        if "R000" in tr.text:
            for td in tr.findAll('td'):
                if td.text != "":
                    indv_prop.append(td.text)

        property_info.append(indv_prop)
        indv_prop = []

    return property_info


def single_lookup(property_id):
    create_files()
    valuation = []
    improvements = []
    taxes = []
    str_url = "{}{}".format(base_url, property_id)
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
    try:
        address = get_address(bs)
    except:
        write_error(property_id, 'address error')
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
    with open('summary.txt', 'w') as outfile:
        for item in summary_headers:
            outfile.write("{},".format(item))
    with open('errors.txt', 'w') as outfile:
        outfile.write("property_id,error")


def write_error(property_id, error_type):
    with open('errors.txt', 'a', newline='') as outfile:
        outfile.write("{}{}\n".format(property_id, error_type))


def get_metrics(properties, data):
    valuation = []
    improvements = []
    taxes = []
    for property_id in properties:
        url = "{}{}".format(base_url, property_id)
        html_txt = urllib.request.urlopen(url)
        bs = BeautifulSoup(html_txt, "lxml")
        for sublist in data:
            if property_id in sublist:
                print("------------------------------")
                print("Address: {}".format(sublist[3]))
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


def get_address(soup):
    address = soup.find(lambda tag: tag.has_attr('id') and tag['id'] == "webprop_situs").get_text()
    print(address)


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
