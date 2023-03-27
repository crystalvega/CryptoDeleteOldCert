from os import path, getcwd, chdir
import PySimpleGUI as sg
import subprocess, os
import win32security
from winreg import *

registry = ConnectRegistry(None, HKEY_LOCAL_MACHINE)

user_info = win32security.LookupAccountName(None,os.getlogin())
sid = win32security.ConvertSidToStringSid(user_info[0])

def ParseCerts(text):
    if 'Subject' in text:
        CONFS = ['Subject', 'Not valid after', 'SHA1 Hash', 'Container']
    elif 'Субъект' in text:
        CONFS = []
    else:
        sg.Popup('Ошибка!\nВ системе не обнаружены ЭЦП.')
        exit()
    i = 0
    textformated = [[]]
    returnvalue = []
    textlines = text.split('\n')
    for line in textlines:
        if str(i+1)+'-------' in line:
            i+=1
            textformated.append([])
        line = line.split(' : ')
        if len(line) != 1:
            textformated[i].append(line)
    del textformated[0]
    for i, certs in enumerate(textformated):
        returnvalue.append([])
        for cert in certs:
            for conf in CONFS:
                if conf in cert[0]:
                    returnvalue[i].append(cert[1])
    for i in range(0, len(returnvalue)):
        if 'CN=' in returnvalue[i][0]:
            returnvalue[i][0] = returnvalue[i][0].split('CN=')[1]
        returnvalue[i][2] = returnvalue[i][2].split('  ')[0]
    return returnvalue
        

def ParseCert1(text):
    while "  " in text:
        text = text.replace("  ", " ")
    while '""' in text:
        text = text.replace('""', '"')
    if 'Subject : ' in text:
        sname = 'Subject : '
    elif 'Субъект : ' in text:
        sname = 'Субъект : '
    else:
        sg.Popup('Ошибка!\nВ системе не обнаружены ЭЦП.')
        exit()
    if 'SHA1 Hash' in text:
        snameSHA = 'SHA1 Hash'
        sSHA = 12
        NVA = 'Not valid after'
        sNVA = 18
        sCont = 12
        Cont = 'Container'
    else:
        snameSHA = 'SHA1 отпечаток'
        sSHA = 17
        NVA = 'Истекает : '
        sNVA = 11
        sCont = 12
        Cont = 'Контейнер'

    start = 0
    g = []
    org = []
    s = 0
    while start < (len(text)):
        cn1 = text.find(sname, start)
        if cn1 == -1:
            break
        cn2 = text.find('\n', cn1)
        organ = text[cn1 + 10:cn2]
        start = cn2
        cn1 = text.find(Cont, start)
        if cn1 == -1:
            break
        cn2 = text.find('\n', cn1)
        organ += ', CO=' + text[cn1 + sCont:cn2]
        start = cn2
        cn1 = text.find(snameSHA, start)
        if cn1 == -1:
            break
        cn2 = text.find('\n', cn1)
        organ += ', KeyID=' + text[cn1 + sSHA:cn2]
        start = cn2
        cn1 = text.find(NVA, start)
        if cn1 == -1:
            break
        cn2 = text.find('\n', cn1)
        organ += ', NVA=' + text[cn1 + sNVA:cn1 + sNVA + 10]
        start = cn2
        g.append(organ)
    for i in g:
        ii = i.split(', ')
        name = ['', '', '', '', '', '']
        for l in ii:
            if l[0:3] == "OID":
                oidinn = l.split('=')
                name[1] = str(int(oidinn[1]))
            if l[0:3] == "CN=":
                name[0] = l[3:].lstrip('"')
            if l[0:6] == "KeyID=":
                name[3] = l[6:]
            if l[0:4] == "NVA=":
                name[4] = l[4:]
            if l[0:2] == "G=":
                name[2] = l[2:] + ')'
            if l[0:3] == "CO=":
                name[5] = l[3:]
            if l[0:3] == "SN=":
                name[2] = '(' + l[3:] + ' ' + name[2]
            if l[0:4] == "ИНН=" and name[1] == '':
                name[1] = l[4:].lstrip("0")
        if name[0] != '' and name[1] != '':
            org.append((name[0], name[4], name[3], name[5]))
    if len(org) == 0:
        sg.Popup('Ошибка!\nНе удалось обработать список ЭЦП.')
        exit()
    return org

def GetCerts():
    global certp
    certp, cspp = CheckCryptoPro()
    cwd = getcwd()
    try:
        chdir(certp)
        result = subprocess.run(['certmgr.exe', '-list', '-verbose', '-store', 'uMy'], shell=True, capture_output=True, text=True, encoding='866').stdout
    except:
        sg.Popup('Произошла ошибка запуска ПО Крипто ПРО.')
        exit()
    chdir(cwd)
    parsecerts = ParseCerts(result)
    parsecertswithck = FindClosedContainer(parsecerts)
    return parsecertswithck

def CheckCryptoPro():
    if path.exists(r'C:\Program Files\Crypto Pro\CSP\csptest.exe'):
        cspp = r'C:\Program Files\Crypto Pro\CSP\csptest.exe'
        certp = 'C:\Program Files\Crypto Pro\CSP'
    elif path.exists(r'C:\Program Files (x86)\Crypto Pro\CSP\csptest.exe'):
        cspp = r'C:\Program Files (x86)\Crypto Pro\CSP\csptest.exe'
        certp = 'C:\Program Files (x86)\Crypto Pro\CSP'
    else:
        sg.Popup('Ошибка!\nПрограммное обеспечение Крипто ПРО не найдено.')
        exit()
    return certp, cspp

def FindCKInReg(nameck):
    try:
        rawKeyA = OpenKey(registry, "SOFTWARE\\WOW6432Node\\Crypto Pro\\Settings\\Users\\" + sid + "\\Keys\\" + nameck)
        CloseKey(rawKeyA)
        return "SOFTWARE\\WOW6432Node\\Crypto Pro\\Settings\\Users\\" + sid + "\\Keys\\" + nameck
    except:
        return None

def FindClosedContainer(certs):
    chdir(certp)
    datasaved = []
    returnvalue = []
    result = subprocess.run(['csptest.exe', '-keyset', '-enum_cont', '--verifycontext', '--fqcn'], shell=True, capture_output=True, text=True, encoding='866').stdout
    closedcon = result.split('\n')
    for cert in certs:
        if len(cert) < 4:
            returnvalue.append(None)
            datasaved.append('N')
        else:
            if '\\\\' in cert[3]:
                cert[3] = cert[3].replace('\\\\', '\\')
            for con in closedcon:
                if cert[3] in con:
                    if con.startswith('\\\\.\\REGISTRY\\'):
                        dir_ck = FindCKInReg(con.replace('\\\\.\\REGISTRY\\',''))
                        datasaved.append('R')
                    returnvalue.append(dir_ck)
    for i in range(0,len(certs)):
        if len(certs[i]) > 3:
            certs[i][3] = returnvalue[i]
            certs[i].append(datasaved[i])
        else:
            certs[i].append(returnvalue[i])
            certs[i].append(datasaved[i])
    return certs

def DeleteCK(key1, key2=''):
    
    if key2=="":
        currentkey = key1
    else:
        currentkey = key1+ "\\" +key2
    
    open_key = OpenKey(registry, key1 ,0,KEY_ALL_ACCESS)
    infokey = QueryInfoKey(open_key)
    for x in range(0, infokey[0]):
        #NOTE:: This code is to delete the key and all subkeys.
        #  If you just want to walk through them, then 
        #  you should pass x to EnumKey. subkey = _winreg.EnumKey(open_key, x)
        #  Deleting the subkey will change the SubKey count used by EnumKey. 
        #  We must always pass 0 to EnumKey so we 
        #  always get back the new first SubKey.
        subkey = EnumKey(open_key, 0)
        try:
            DeleteKey(open_key, subkey)
            print ("Removed %s\\%s " % ( key1, subkey))
        except:
            DeleteCK(registry, currentkey, subkey )
            # no extra delete here since each call 
            #to deleteSubkey will try to delete itself when its empty.

    DeleteKey(open_key,"")
    open_key.Close()
    print("Removed %s" % (currentkey))

def Delete(certs):
    chdir(certp)
    certserror =[]
    retvalue = True
    for cert in certs:
        if cert[3] == 'R':
            DeleteCK(cert[2])
        ret = subprocess.run(['certmgr.exe', '-delete', '-thumbprint', cert[1]], shell=True, capture_output=True, text=True, encoding='866').returncode
        if ret != 0:
            certserror.append(cert)
            retvalue = False
    return retvalue, certserror
