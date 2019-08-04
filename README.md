# [BootsRoas](https://www.boostroas.com/) HeyBooster

**Proje Bilgileri**
* **Framework**: Flask==1.1.1

**Yapılacaklar**
* ~~Kanala Slack Bot Bağlama ve Veri Yollama~~
* ~~Google analytics hesabı bağlama~~
* Bağlanan hesapların verilerini çekme

---

**Alınabilecek Hatalar**
```
oauthlib.oauth2.rfc6749.errors.InsecureTransportError

oauthlib.oauth2.rfc6749.errors.InsecureTransportError: (insecure_transport) OAuth 2 MUST utilize https.
```
**Çözüm:** export OAUTHLIB_INSECURE_TRANSPORT=1

---

```
flask-oauthlib 0.9.5 has requirement oauthlib!=2.0.3,!=2.0.4,!=2.0.5,<3.0.0,>=1.1.2, but you'll have oauthlib 3.0.2 which is incompatible.
```
**Çözüm:** pip3 install Authlib