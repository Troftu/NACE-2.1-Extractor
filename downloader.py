from bs4 import BeautifulSoup
import requests
import csv
import json
import re

class NaceTableEntry:
    def __init__(self, cols):     
        self.division = cols[0]
        self.group = cols[1]
        self.classId = cols[2]
        self.description = cols[3]

    def __str__(self):
        return f"{self.division} {self.group} {self.classId} - {self.description}"
    
    def __repr__(self):
        return f"{self.division}{self.group}{self.classId} "

class TableDownloader:
    def __init__(self, isoLangCode):
        self.isoLangCode = isoLangCode
        self.url = f"https://eur-lex.europa.eu/legal-content/{isoLangCode}/TXT/HTML/?uri=CELEX:32023R0137"
        self.table = []

    def fetch_data(self):
        response = requests.get(self.url)
        soup = BeautifulSoup(response.content.decode('utf-8'), 'html.parser')
        # The id needs to match a regex cause there is a language code in there, that we could
        # build using isoLangCode, but can also look past for more robustness
        div = soup.find(id=re.compile(r"L_2023019[A-Z]{2}\.01000901"))
        htmlRows = div.find_all('tr', class_='oj-table')

        # Iterate over all rows and read data cells 0-4 into their corresponding fields
        for tr in htmlRows[1:]:
            cols = [td.get_text(strip=True) for td in tr.find_all('td')]
            self.table.append(NaceTableEntry(cols))

    def get_table(self):
        return self.table

class NaceCode:
    def Empty():
        return NaceCode("", "")

    def __init__(self, code, description):
        self.code = code.strip()
        self.description = description.strip()

        self.codeNoDot = self.code.replace(".", "")
        self.divisionId = int(self.codeNoDot[0:2]) if (len(self.codeNoDot) >= 1 and self.codeNoDot.isnumeric()) else None
        self.groupId = int(self.codeNoDot[2]) if len(self.codeNoDot) > 2 else None
        self.classId = int(self.codeNoDot[3]) if len(self.codeNoDot) > 3 else None

        self.isSection = not self.codeNoDot.isnumeric()
        self.isDivision = self.divisionId != None and self.groupId == None and self.classId == None
        self.isGroup = self.groupId != None and self.classId == None
        self.isClass = self.classId != None

        self.children = []

class HierarchyBuilder:
    def __init__(self, naceTable, sectionCodeParsingFunc, sectionDescriptionParsingFunc):
        self.naceTable = naceTable
        self.sectionCodeParsingFunc = sectionCodeParsingFunc
        self.sectionDescriptionParsingFunc = sectionDescriptionParsingFunc

    def get_hierarchical_representation(self):
        naceHierarchy = []
        section = None
        division = None
        group = None
        for row in self.naceTable:
            naceCode = NaceCode(row.division + row.group + row.classId, row.description)
            if naceCode.codeNoDot == "":
                naceCode = NaceCode(self.sectionCodeParsingFunc(row.description),
                                    self.sectionDescriptionParsingFunc(row.description))
            if (naceCode.isSection):
                if (section != None): 
                    naceHierarchy.append(section)
                section = naceCode
            elif (naceCode.isDivision):
                division = naceCode
                section.children.append(division)
            elif (naceCode.isGroup):
                group = naceCode
                division.children.append(group)
                group = naceCode
            elif (naceCode.isClass):
                group.children.append(naceCode)
            else:
                print("Error: NaceCode not recognized " + naceCode.code)

        return naceHierarchy
    
class JsonExporter:
    def __init__(self, naceCodes, filename):
        self.naceCodes = naceCodes
        self.filename = filename

    def save(self):
        jsonData = json.dumps(self.naceCodes, indent=4, default=vars, ensure_ascii=False)
        with open(self.filename,"w",encoding="utf-8") as jsonFile:
            jsonFile.write(jsonData)
    
class CsvExporter:
    def __init__(self, naceCodes, encoding, filename, delimiter, escapeChar, linebreak):
        self.naceCodes = naceCodes
        self.filename = filename
        self.delimiter = delimiter
        self.escapeChar = escapeChar
        self.linebreak = linebreak
        self.encoding = encoding

    def save(self):
        with open("output.csv", "w", encoding=self.encoding, newline="\r\n") as csvfile:
            writer = csv.writer(csvfile,
                                delimiter=self.delimiter,
                                escapechar=self.escapeChar,
                                lineterminator=self.linebreak)

            for code in self.naceCodes:
                writer.writerow(code)

extractor = TableDownloader("DE")
extractor.fetch_data()
table = extractor.get_table()

hierarchy = HierarchyBuilder(table, lambda x: re.match(r"^ABSCHNITT\s([A-Z])\s—\s(.+)$", x).group(1),lambda x: re.match(r"^ABSCHNITT\s([A-Z])\s—\s(.+)$", x).group(2).title())
hierarchical = hierarchy.get_hierarchical_representation()           

JsonExporter(hierarchical, "output2.json").save()
# Use the class
#extractor = DataExtractor(url)
#extractor.fetch_data()
#extractor.to_csv('output.csv')
#extractor.to_json('output.json')
