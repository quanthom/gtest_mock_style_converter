import os
import sys
import re
import hamcrest
import argparse

MOCK_METHOD_OLD_METHODS = [{'pattern': r'MOCK_METHOD\d+', 'extension': '(override)'},
                           {'pattern': r'MOCK_CONST_METHOD\d+', 'extension': '(const, override)'}]

def list_all_files(path):
    files_path = []
    for root, dirs, files in os.walk(path):
        for file in files:
            files_path.append(os.path.join(root, file))
            files_path[-1] = files_path[-1].replace('\\', '/') # make unix path format
                
    return files_path

def unfold_multilines_statements(lines):
    out = []
    aggregate = False
    for line in lines:
        if not aggregate:
            for method in MOCK_METHOD_OLD_METHODS:
                pattern = '^\s*' + method['pattern'] + '.*,$'
                if re.search(pattern, line):
                    out.append(line[:-1])# remove newline character
                    aggregate = True
                    break
            if not aggregate:
                out.append(line)
        else:
            out[-1] += line[:-1]
            if re.search('^.*;$', line):
                aggregate = False # end of multiline MOCK_METHOD

    return out

def read_text_from_file(filepath):
    if re.search('\.[h|c](?:pp)?$', filepath): # Only open header files
        with open(filepath, 'rU') as file:
            lines = file.readlines()
            file.close()
            lines = unfold_multilines_statements(lines)
            return lines
    else:
        return None
    
def write_text_to_file(filepath, lines):
    file = open(filepath, 'w')
    file.writelines(lines)
    file.close()
    
def convert_mock_method(args):
    trailingWs = args.group(1)
    inputLine = args.group(2)
    mock_method_params = args.group(3)
    p = re.compile('^\s*([\w|#]+)\s*,\s*(\(?[^\)\(]+\)?)\((.*)\)\s*$')
    args = p.findall(mock_method_params)
    try:
        args = args[0] # extract tuple from list
    except IndexError as error:
        print(inputLine)

    methodName = args[0]
    returnType = args[1]
    mockMethodArgs = args[2]

    p = re.compile('([^<^,]+(?:<[^\(\)>]+>[^,]+)?)')
    args = p.findall(mockMethodArgs) # list of method arguments
    for i in range(0, len(args)):
        args[i] = re.sub('^\s*', '', re.sub('\s*$', '', args[i])) # remove trailing whitespaces

    if args == ['void']: # Compilation error bug: (void) replaced by ()
        args = []

    convertedLine = trailingWs
    convertedLine += "MOCK_METHOD("
    convertedLine += returnType + ", "
    indentLength = len(convertedLine)-1
    convertedLine += methodName + ", "
    offset = 0

    for index,arg in enumerate(args):
        if index == 0:
            nextArg = "(" + arg
            if index is len(args)-1:
                nextArg += ")"
            else:
                nextArg += ","
        elif index == len(args)-1:
            nextArg = " " + arg + ")"
        else:
            nextArg = " " + arg + ","

        if len(convertedLine + nextArg) - offset > 80:
            offset = len(convertedLine)
            if index < 1: # align with method name
                convertedLine = convertedLine[:-1] # Remove whitespace
            convertedLine += "\n" + " " * indentLength
        else:
            if index < 1: # align with first argument
                indentLength = len(convertedLine)
        convertedLine += nextArg

    if args == []:
        convertedLine += '()'

    return convertedLine

def extract_mock_methodn(inputLine):
    for method in MOCK_METHOD_OLD_METHODS:
        pattern = '^(\s*)(' + method['pattern'] + '\s*\((.*)\);)$'
        matches = re.search(pattern, inputLine)
        if matches:
            convertedLine = convert_mock_method(matches)
            if method['extension']:
                convertedLine += ', ' + method['extension']
            convertedLine += ');'
            return convertedLine
    return None
        
def extract_mock_const_methodn(inputLine):
    matches = re.search('^(\s*)(MOCK_CONST_METHOD\d+\s*\((.*)\);)$', inputLine)
    if matches:
        [convertedLine, args] = convert_mock_method(matches)
        if args:
            convertedLine = convertedLine[:-1] + "), (const, override));"
        else:
            convertedLine += "(), (const, override));"

        return convertedLine
    else:
        return None
        
def extract_mock_methodn_t(inputLine):
    matches = re.search('^MOCK_METHOD\d_T\s*\((.*)\);$', inputLine)
    if matches:
        print(inputLine + " is MOCK_METHODn_T")
        
def extract_mock_const_methodn_t(inputLine):
    matches = re.search('^MOCK_CONST_METHOD\d_T\s*\((.*)\);$', inputLine)
    if matches:
        print(inputLine + " is MOCK_CONST_METHODn_T")
        
def extract_mock_methodn_with_calltype(inputLine):
    matches = re.search('^MOCK_METHOD\d_WITH_CALLTYPE\s*\((.*)\);$', inputLine)
    if matches:
        print(inputLine + " is MOCK_METHODn_WITH_CALLTYPE")
        
def extract_mock_const_methodn_with_calltype(inputLine):
    matches = re.search('^MOCK_CONST_METHOD\d_WITH_CALLTYPE\s*\((.*)\);$', inputLine)
    if matches:
        print(inputLine + " is MOCK_CONST_METHODn_WITH_CALLTYPE")
        
def extract_mock_methodn_t_with_calltype(inputLine):
    matches = re.search('^MOCK_METHOD\d_T_WITH_CALLTYPE\s*\((.*)\);$', inputLine)
    if matches:
        print(inputLine + " is MOCK_METHODn_T_WITH_CALLTYPE")
        
def extract_mock_const_methodn_t_with_calltype(inputLine):
    matches = re.search('^MOCK_CONST_METHOD\d_T_WITH_CALLTYPE\s*\((.*)\);$', inputLine)
    if matches:
        print(inputLine + " is MOCK_CONST_METHODn_T_WITH_CALLTYPE")

def convert_to_new_format(lines):
    log = []
    for line in lines:
        convertedLine = extract_mock_methodn(line)
        if convertedLine:
            lines[lines.index(line)] = convertedLine + '\n'
            log.append(re.search('^\s*(.*)$', line, re.MULTILINE).group(1) + " was converted to: " + re.search('^\s*(.*)$', convertedLine, re.MULTILINE).group(1))
    return [lines, log]
   

def main():        
    parser = argparse.ArgumentParser(description='Script converting old-fashioned MOCK_METHODn format to new format')
    parser.add_argument('path', nargs='?',default='.')
    parser.add_argument('-e', '--exclude')
    args = parser.parse_args()

    files = list_all_files(args.path)
    if args.exclude:
        excluded_paths = args.exclude.split(',')
        excluded_files = []
        for path in excluded_paths:
            excluded_files += list_all_files(path)

        for file in excluded_files:
            if file in files:
                files.remove(file)

    for i in range(0, len(files)):
        inLines = read_text_from_file(files[i])
        if inLines:
            [outLines, log] = convert_to_new_format(inLines)
            for convertedLine in log:
                print('\033[92m' + '\033[1m' + files[i] + ': \033[0m' + convertedLine)
            if log: # lines have been converted
                write_text_to_file(files[i], outLines)
    
if __name__ == '__main__':
    main()
    