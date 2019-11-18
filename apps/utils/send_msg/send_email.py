#!/usr/bin/env python
# -*-coding:utf-8-*-
# @Time : 2017/11/1 ~ 2019/9/1
# @Author : Allen Woo
import time
from flask_mail import Message
from apps.core.plug_in.manager import plugin_manager
from apps.routing.theme_views import get_render_template_email
from apps.utils.osr_async.osr_async import async_process
from apps.app import mail, app, mdbs

__author__ = 'woo'


def send_email(msg="", tp_path=None, tp_data=None, send_independently=True):
    """
    Send email
    :return:
    """
    if "html_msg" in msg:
        html = msg["html_msg"]
    else:
        html = get_render_template_email(path=tp_path, params=tp_data)
    if html:
        send_async_email(msg=msg, html=html, text="", send_independently=send_independently)
    else:
        status = "failed"
        log = {
            'status': status,
            'time': time.time(),
            "msg": "Failed to get template"
        }

        mdbs["site"].db.sys_email_log.insert_one(log)


# 之后需要改成celery异步
@async_process()
def send_async_email(msg, html, text, attach=None, send_independently=True):
    """
    发送email
    :param subject:
    :param recipients:数组
    :param text:
    :param html:
    :param attach:(<filename>,<content_type>)
    :param send_independently:如果为True, 独立给recipients中的每个地址发送信息,
            否则,一次发送, 收件人能看到其他收件人的邮箱

    :return:
    """

    # 检测插件
    data = plugin_manager.call_plug(hook_name="send_email",
                                    send_independently=send_independently,
                                    msg=msg,
                                    html=html,
                                    text=text,
                                    attach=attach)
    if data == "__no_plugin__":

        with app.app_context():
            msg_obj = Message(
                subject=msg["subject"],
                html=html
            )

            if send_independently:
                # 独立发送, 先连接好邮件服务器
                with mail.connect() as conn:
                    for recipient in msg["recipients"]:
                        msg_obj.recipients = [recipient]
                        send_email_process(msg_obj, conn)
            else:
                msg_obj.recipients = msg["recipients"]
                return send_email_process(msg_obj)


def send_email_process(msg_obj, connected_instance=None):
    """
    发送
    :param msg:
    :param connected_instance: 已连接的实例
    :return:
    """
    result_msg = "Send a success"
    try:
        if connected_instance:
            r = connected_instance.send(msg_obj)
        else:
            r = mail.send(msg_obj)
        if not r:
            status = "successful"
        else:
            status = "abnormal"
    except Exception as e:
        result_msg = str(e)
        status = "error"
    log = {
        "type": "email",
        "error_info": result_msg,
        'status': status,
        'subject': msg_obj.subject,
        'from': msg_obj.sender,
        'to': list(msg_obj.send_to),
        'date': msg_obj.date,
        'body': msg_obj.body,
        'html': msg_obj.html,
        'msgid': msg_obj.msgId,
        'time': time.time()

    }
    mdbs["sys"].db.sys_message.insert_one(log)
