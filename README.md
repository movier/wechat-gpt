# 扫码关注公众号体验 GPT-4
<img src="qrcode.jpeg" width="200">

# 准备工作
1. 获取OpenAI的API KEY
2. 获取微信公众号APP_ID、APP_KEY和TOKEN（确保公众号具有**发送消息-客服接口**接口，具体信息可以查看微信公众号的[接口权限说明](https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Explanation_of_interface_privileges.html)，个人可以使用[微信公众平台接口测试帐号](https://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login)）
3. （可选）获取腾讯云的SECRET_ID、SECRET_KEY、BUCKET_REGION和BUCKET_NAME（如果要使用腾讯云的文本审核）

# 开发
1. 运行脚本`./build.sh`构建镜像
2. 运行脚本`./run.sh`启动容器
