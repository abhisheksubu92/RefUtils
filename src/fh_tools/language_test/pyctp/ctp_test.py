# -*- coding: utf-8 -*-
"""
Created on 2017/5/11
@author: MG
"""

# -*- coding: utf-8 -*-

import hashlib, os, sys, tempfile, time
# 通过以下方式使用期货/股票版API
from ctp import ApiStruct, MdApi


class MyMdApi(MdApi):
    def __init__(self, brokerID, userID, password, instrumentIDs):
        self.requestID = 0
        self.brokerID = brokerID
        self.userID = userID
        self.password = password
        self.instrumentIDs = instrumentIDs
        self.Create()

    def Create(self):
        dir = b''.join((b'ctp.futures', self.brokerID, self.userID))
        dir = hashlib.md5(dir).hexdigest()
        dir = os.path.join(tempfile.gettempdir(), dir, 'Md') + os.sep
        if not os.path.isdir(dir): os.makedirs(dir)
        MdApi.Create(self, os.fsencode(dir) if sys.version_info[0] >= 3 else dir)

    def RegisterFront(self, front):
        if isinstance(front, bytes):
            return MdApi.RegisterFront(self, front)
        for front in front:
            MdApi.RegisterFront(self, front)

    def OnFrontConnected(self):
        print('OnFrontConnected: Login...')
        req = ApiStruct.ReqUserLogin(
            BrokerID=self.brokerID, UserID=self.userID, Password=self.password)
        self.requestID += 1
        self.ReqUserLogin(req, self.requestID)

    def OnFrontDisconnected(self, nReason):
        print('OnFrontDisconnected:', nReason)

    def OnHeartBeatWarning(self, nTimeLapse):
        print('OnHeartBeatWarning:', nTimeLapse)

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        print('OnRspUserLogin:', pRspInfo)
        if pRspInfo.ErrorID == 0: # Success
            print('GetTradingDay:', self.GetTradingDay())
            self.SubscribeMarketData(self.instrumentIDs)

    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        print('OnRspSubMarketData:', pRspInfo)

    def OnRspUnSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        print('OnRspUnSubMarketData:', pRspInfo)

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        print('OnRspError:', pRspInfo)

    def OnRspUserLogout(self, pUserLogout, pRspInfo, nRequestID, bIsLast):
        print('OnRspUserLogout:', pRspInfo)

    def OnRtnDepthMarketData(self, pDepthMarketData):
        print('OnRtnDepthMarketData:', pDepthMarketData)

if __name__ == '__main__':
    mdapi = MyMdApi(b'9999', b'13522870868', b'12348765', [b'rb1712'])
    mdapi.RegisterFront(b'tcp://180.168.146.187:10010')
    mdapi.Init()

    try:
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
