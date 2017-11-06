import re,requests
class Getmyip:
    def getip(self):
        try:
            myip = self.visit("http://www.ip138.com/ip2city.asp")
        except:
            try:
                myip = self.visit("http://www.ip138.com/ip2city.asp")
            except:
                try:
                    myip = self.visit("http://www.ip138.com/ip2city.asp")
                except:
                    myip = "So sorry!!!"
        return myip
    def visit(self,url):
        res = requests.get(url)
        print res
        emm = res.text
        # opener = urllib2.urlopen(url)
        # print opener
        # if url == opener.geturl():
        #     str = opener.read()
        #     print str
        return re.search('\d+\.\d+\.\d+\.\d+', emm).group(0)

if 'main'=='__name__':
    getmyip = Getmyip()
    localip = getmyip.getip()
    print localip