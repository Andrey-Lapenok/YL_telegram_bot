import smtplib

server = 'smtp.email.ru'
user = 'andrey.lapenok@gmail.com'
password = 'vrjyekiigondxumy'
recipient = 'andrey.lapenok@gmail.com'

smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
smtpObj.starttls()
smtpObj.login(user, password)
smtpObj.sendmail(user, recipient, "go to bed!")
smtpObj.quit()
