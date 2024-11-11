import eel
import os
import pathlib
import datetime
import sys
from dotenv import load_dotenv, dotenv_values
import replicate
import imaplib
import email
import email.parser
import email.header
from bs4 import BeautifulSoup 
import pickle
import uuid
import shutil
import llmmodule
from OSMPythonTools.nominatim import Nominatim
import smtplib
from email.mime.text import MIMEText

nominatim = Nominatim()

config = dict(dotenv_values())

imap_user = config["IMAP_USER"]
imap_pass = config["IMAP_PASS"]
imap_host = config["IMAP_HOST"]
smtp_host = config["SMTP_HOST"]

imap = imaplib.IMAP4_SSL(imap_host)
imap.login(imap_user, imap_pass)

smtp = smtplib.SMTP_SSL(smtp_host)
smtp.login(imap_user, imap_pass)

os.chdir(os.path.dirname(os.path.realpath(__file__)))

"""
=============================
        LOADING MAILS
=============================
"""    

@eel.expose
def load_prevmail():
    imap.select('Inbox', readonly=True)

    (retcode, msgnums) = imap.search(None, "(SEEN)")
    assert retcode == "OK"

    mails = []
    for msg in  msgnums[0].split():
        mail = {}

        _, data = imap.fetch(msg, "(RFC822)")
        message = email.parser.BytesParser().parsebytes(data[0][1])

        mail["msgnumber"] = msg
        mail["from"] = message.get("From")
        mail["to"] = message.get("To")
        mail["date"] = message.get("Date")

        mimeSubject = message.get("Subject")
        decodedSubject = email.header.decode_header(mimeSubject)
        mail["subject"] = str(email.header.make_header(decodedSubject))
        
        mail["minicontent"] = ""
        mail["content"] = ""

        for part in message.walk():
            if part.get_content_type() == "text/plain":
                mail["minicontent"] += part.get_payload(decode=True).decode()
            elif part.get_content_type() == "text/html":
                if not pathlib.Path('./web/userData').exists(): pathlib.Path('./web/userData').mkdir(parents=True)
                with open(f'./web/userData/{msg.decode()}-mail.html', 'w', encoding='utf-8') as file:
                    file.write(part.get_payload(decode=True).decode())
                mail["content"] = f'./userData/{msg.decode()}-mail.html'
                
        
        if mail['content'] == '':
            mail['textOnly'] = True
        
        mails.append(mail)
    
    imap.unselect()

    return mails

@eel.expose
def SearchMail(searchString):
    imap.select('Inbox', readonly=True)

    (retcode, msgnums) = imap.search(None, "(TEXT %s)" % searchString)
    assert retcode == "OK"

    mails = []
    for msg in  msgnums[0].split():
        mail = {}

        _, data = imap.fetch(msg, "(RFC822)")
        message = email.parser.BytesParser().parsebytes(data[0][1])

        mail["msgnumber"] = msg
        mail["from"] = message.get("From")
        mail["to"] = message.get("To")
        mail["date"] = message.get("Date")

        mimeSubject = message.get("Subject")
        decodedSubject = email.header.decode_header(mimeSubject)
        mail["subject"] = str(email.header.make_header(decodedSubject))
        
        mail["minicontent"] = ""
        mail["content"] = ""

        for part in message.walk():
            if part.get_content_type() == "text/plain":
                mail["minicontent"] += part.get_payload(decode=True).decode()
            elif part.get_content_type() == "text/html":
                if not pathlib.Path('./web/userData').exists(): pathlib.Path('./web/userData').mkdir(parents=True)
                with open(f'./web/userData/{msg.decode()}-mail.html', 'w', encoding='utf-8') as file:
                    file.write(part.get_payload(decode=True).decode())
                mail["content"] = f'./userData/{msg.decode()}-mail.html'
                
        
        if mail['content'] == '':
            mail['textOnly'] = True
        
        mails.append(mail)
    
    imap.unselect()

    return mails

@eel.expose
def loadNewMail():
    imap.select('Inbox', readonly=True)

    (retcode, msgnums) = imap.search(None, "(UNSEEN)")
    assert retcode == "OK"

    mails = []
    for msg in  msgnums[0].split():
        mail = {}

        _, data = imap.fetch(msg, "(RFC822)")
        message = email.parser.BytesParser().parsebytes(data[0][1])

        mail["msgnumber"] = msg.decode('utf-8')
        mail["from"] = message.get("From")
        mail["to"] = message.get("To")
        mail["date"] = message.get("Date")

        mimeSubject = message.get("Subject")
        decodedSubject = email.header.decode_header(mimeSubject)
        mail["subject"] = str(email.header.make_header(decodedSubject))

        mail["minicontent"] = ""
        mail["content"] = ""

        for part in message.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                try:
                    # Try UTF-8 decoding first
                    mail["minicontent"] += payload.decode('utf-8')
                except UnicodeDecodeError:
                    # Fallback to latin-1 decoding if UTF-8 fails
                    mail["minicontent"] += payload.decode('latin-1')
            elif part.get_content_type() == "text/html":
                if not pathlib.Path('./web/userData').exists():
                    pathlib.Path('./web/userData').mkdir(parents=True)
                with open(f'./web/userData/{msg.decode()}-mail.html', 'w', encoding='utf-8') as file:
                    file.write(part.get_payload(decode=True).decode('utf-8', errors='ignore'))
                mail["content"] = f'./userData/{msg.decode()}-mail.html'

        if mail['content'] == '':
            mail['textOnly'] = True

        mails.append(mail)

    imap.unselect()

    return mails


"""
============================
        MODIFY MAILS
============================
"""

@eel.expose
def markAsRead(msgnumber):
    imap.select('Inbox')
    imap.store(msgnumber, '+FLAGS','\Seen')
    imap.unselect()

@eel.expose
def deleteMail(msgnumber):
    imap.select('Inbox')
    imap.store(msgnumber, '+FLAGS', '\\Deleted')
    imap.expunge()
    imap.unselect()

@eel.expose
def sendMail(body, toList, subject):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = imap_user
    msg['To'] = ', '.join(toList)
    smtp.sendmail(imap_user, ', '.join(toList), msg.as_string())
    print("MAIL SENT SUCCESSFULLY")

"""
============================
        SAVE MAILS
============================
"""

@eel.expose
def fetchSavedMail():
    with open('./web/userData/newData', 'rb') as file:
        mailsObject = pickle.load(file)
        return mailsObject

@eel.expose()
def saveMail(mailObject):
    uuidId = str(uuid.uuid4())
    oldcontentPath = pathlib.Path('./web').joinpath(pathlib.Path(mailObject['content']))
    newContentPath = pathlib.Path(f'./web/userData/{uuidId}.html')

    shutil.copyfile(oldcontentPath, newContentPath)
    mailObject['content'] = f'./userData/{uuidId}.html'

    if not pathlib.Path("./web/userData/newData").exists():
        file = open('./web/userData/newData', 'wb')
        pickle.dump([mailObject], file)
        file.close()
        return

    file = open('./web/userData/newData', 'rb')
    mailsObject = pickle.load(file)
    mailsObject.append(mailObject)
    file.close()
    
    file = open('./web/userData/newData', 'wb')
    pickle.dump(mailsObject, file)

"""
=============================
        CLOSE PYTHON
=============================
"""

@eel.expose
def close_python(page, sockets_still_open):
    sys.exit(0)

"""
=======================
        LLM
=======================
"""

@eel.expose
def summarizeEmail(text):
    return llmmodule.summarizeThis(text)

@eel.expose
def generateResponseToMail(text):
    return llmmodule.generateResponse(text)

@eel.expose
def getJsonData(text):
    return llmmodule.jsonExtractor(text)

@eel.expose
def extractActionItemsJSON(text):
    try:
        return llmmodule.generateActionItems(text)
    except:
        return {'items': []}

@eel.expose
def addTaskList(subject, taskList):
    print("CALLED")
    if not pathlib.Path('./web/userData/tasklists.txt').exists():
        taskLists = []
        with open('./web/userData/tasklists.txt', 'wb') as file:
            pickle.dump(taskLists, file)
    
    file = open('./web/userData/tasklists.txt', 'rb')
    taskLists = pickle.load(file)
    file.close()

    taskLists.append({"title": subject, "taskList": taskList})

    file = open('./web/userData/tasklists.txt', 'wb')
    pickle.dump(taskLists, file)
    file.close()

@eel.expose
def getTaskLists():
    if not pathlib.Path('./web/userData/tasklists.txt').exists():
        return []
    file = open('./web/userData/tasklists.txt', 'rb')
    returnVal = pickle.load(file)
    file.close()

    return list(returnVal)

@eel.expose
def removeTask(idString):
    i, j = [int(k) for k in idString.split(':')]
    
    file = open('./web/userData/tasklists.txt', 'rb')
    obj = pickle.load(file)
    file.close()

    del obj[i]['taskList']['items'][j]
    if obj[i]['taskList']['items'] == []:
        del obj[i]
    
    file = open('./web/userData/tasklists.txt', 'wb')
    pickle.dump(obj, file)
    file.close()

    print(f"DELETED {i}:{j}")

@eel.expose
def getLocationLatLong(text):
    location = getJsonData(text)['location']
    data = nominatim.query(location)
    jsonData = data.toJSON()
    if jsonData == []:
        return [
            0,0,
            f"Could not find a location. Sorry! Nominatim couldn't find the {location}"
        ]
    returnData = [
        jsonData[0]['lat'],
        jsonData[0]['lon'],
        jsonData[0]['display_name']
    ]
    return returnData

@eel.expose
def testPrompt():
    output = replicate.run("replicate/llama-7b:ac808388e2e9d8ed35a5bf2eaa7d83f0ad53f9e3df31a42e4eb0a0c3249b3165",
                       input = {
                           "debug": False,
                           "top_p": 0.95,
                           "prompt": "Simply put, the theory of relativity states that",
                           "max_length": 500,
                           "temperature": 0.8,
                           "repetition_penalty": 1,
                           "max_length": 400
                       })

    outString = ""

    for item in output:
        outString += item
    
    outString = outString.capitalize()
    
    return outString

"""
=============================
            NOTES 
=============================
"""

@eel.expose
def fetchNotes():
    if not pathlib.Path('./web/userData/notes').exists():
        return []
    return pickle.load(open('./web/userData/notes', 'rb'))

@eel.expose
def saveNote(noteTitle, noteText):
    if not pathlib.Path('./web/userData/notes').exists():
        file = open('./web/userData/notes', 'wb')
        pickle.dump([], file)
        file.close()
    
    file = open('./web/userData/notes', 'rb')
    notesArray = pickle.load(file)
    file.close()

    notesArray.append({
        'title': noteTitle,
        'text': noteText,
    })

    file = open('./web/userData/notes', 'wb')
    pickle.dump(notesArray, file)
    file.close()

@eel.expose
def deleteNote(noteText, noteTitle):
    file = open('./web/userData/notes', 'rb')
    notesArray = pickle.load(file)
    file.close()

    notesArray.remove({
        'title': noteTitle,
        'text': noteText,
    })

    file = open('./web/userData/notes', 'wb')
    pickle.dump(notesArray, file)
    file.close()

"""
=====================
    SET REMINDER
=====================
"""

@eel.expose
def getReminders():
    FILEPATH = 'D:\\reminders.txt'
    DATEONLY = 123
    DATETIME = 321
    DATETIMEFORMAT = '%d-%m-%y-%H-%M-%S'
    DATEONLYFORMAT = '%d-%m-%y'

    reminderFile = open(FILEPATH)

    reminders = []

    for line in reminderFile.readlines():
        remnameString = line.strip().split()
        remname = " ".join(remnameString[:-1])
        remstring = remnameString[-1]
        try:
            reminder = datetime.datetime.strptime(remstring, DATETIMEFORMAT).strftime(DATETIMEFORMAT)
            remType = DATETIME
        except ValueError:
            reminder = datetime.datetime.strptime(remstring, DATEONLYFORMAT).strftime(DATEONLYFORMAT)
            remType = DATEONLY
        
        reminders.append((remname, reminder, remType))

    reminderFile.close()

    return reminders

@eel.expose
def createReminder(dateString, subject):
    dateString = dateString.replace(" ", "")
    try:
        addReminder("_".join(subject.split()), datetime.datetime.strptime(dateString, '%d-%m-%y').strftime("%d-%m-%y"))
    except:
        addReminder(subject, datetime.datetime.strptime(dateString, '%d-%m-%Y').strftime("%d-%m-%y"))
    return "Done"

def addReminder(eventName, dateString):
    file1 = open("D:\\reminders.txt", "r") 
    Lines = file1.readlines()
    print(Lines)

    d={}
    for i in range(len(Lines)):
        st=Lines[i].split()
        d[" ".join(st[:-1])]=st[-1]
    
    d[eventName] = dateString

    final=[]
    file1=open("D:\\reminders.txt","w")
    for i in d:
        st=i+" "+d[i]+"\n"
        file1.write(st)
        final.append({"name":i,"datestring":d[i]})
    print(final)
    file1.close()

if __name__ == "__main__":
    eel.init('web')
    eel.start('main.html')