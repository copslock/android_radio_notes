def get_phone_number_by_adb(ad):
    return phone_number_formatter(
        ad.adb.shell("service call iphonesubinfo 13"))


def get_iccid_by_adb(ad):
    return ad.adb.shell("service call iphonesubinfo 11")


def get_sub_id_by_adb(ad):
    return ad.adb.shell("service call iphonesubinfo 5")

def trigger_modem_crash(ad, timeout=120):
    cmd = "echo restart > /sys/kernel/debug/msm_subsys/modem"
    ad.log.info("Triggering Modem Crash from kernel using adb command %s", cmd)
    ad.adb.shell(cmd)
    time.sleep(timeout)
    return True

def trigger_modem_crash_by_modem(ad, timeout=120):
    begin_time = get_device_epoch_time(ad)
    ad.adb.shell(
        "setprop persist.vendor.sys.modem.diag.mdlog false",
        ignore_status=True)
    # Legacy pixels use persist.sys.modem.diag.mdlog.
    ad.adb.shell(
        "setprop persist.sys.modem.diag.mdlog false", ignore_status=True)
    disable_qxdm_logger(ad)
    cmd = ('am instrument -w -e request "4b 25 03 00" '
           '"com.google.mdstest/com.google.mdstest.instrument.'
           'ModemCommandInstrumentation"')
    ad.log.info("Crash modem by %s", cmd)
    ad.adb.shell(cmd, ignore_status=True)
    time.sleep(timeout)  # sleep time for sl4a stability
    reasons = ad.search_logcat("modem subsystem failure reason", begin_time)
    if reasons:
        ad.log.info("Modem crash is triggered successfully")
        ad.log.info(reasons[-1]["log_message"])
        return True
    else:
        ad.log.warning("There is no modem subsystem failure reason logcat")
        return False

def phone_switch_to_msim_mode(ad, retries=3, timeout=60):
    result = False
    if not ad.is_apk_installed("com.google.mdstest"):
        raise signals.TestAbortClass("mdstest is not installed")
    mode = ad.droid.telephonyGetPhoneCount()
    if mode == 2:
        ad.log.info("Device already in MSIM mode")
        return True
    for i in range(retries):
        ad.adb.shell(
        "setprop persist.vendor.sys.modem.diag.mdlog false", ignore_status=True)
        ad.adb.shell(
        "setprop persist.sys.modem.diag.mdlog false", ignore_status=True)
        disable_qxdm_logger(ad)
        cmd = ('am instrument -w -e request "WriteEFS" -e item '
               '"/google/pixel_multisim_config" -e data  "02 00 00 00" '
               '"com.google.mdstest/com.google.mdstest.instrument.'
               'ModemConfigInstrumentation"')
        ad.log.info("Switch to MSIM mode by using %s", cmd)
        ad.adb.shell(cmd, ignore_status=True)
        time.sleep(timeout)
        ad.adb.shell("setprop persist.radio.multisim.config dsds")
        reboot_device(ad)
        # Verify if device is really in msim mode
        mode = ad.droid.telephonyGetPhoneCount()
        if mode == 2:
            ad.log.info("Device correctly switched to MSIM mode")
            result = True
            if "Sprint" in ad.adb.getprop("gsm.sim.operator.alpha"):
                cmd = ('am instrument -w -e request "WriteEFS" -e item '
                       '"/google/pixel_dsds_imei_mapping_slot_record" -e data "03"'
                       ' "com.google.mdstest/com.google.mdstest.instrument.'
                       'ModemConfigInstrumentation"')
                ad.log.info("Switch Sprint to IMEI1 slot using %s", cmd)
                ad.adb.shell(cmd, ignore_status=True)
                time.sleep(timeout)
                reboot_device(ad)
            break
        else:
            ad.log.warning("Attempt %d - failed to switch to MSIM", (i + 1))
    return result


def phone_switch_to_ssim_mode(ad, retries=3, timeout=30):
    result = False
    if not ad.is_apk_installed("com.google.mdstest"):
        raise signals.TestAbortClass("mdstest is not installed")
    mode = ad.droid.telephonyGetPhoneCount()
    if mode == 1:
        ad.log.info("Device already in SSIM mode")
        return True
    for i in range(retries):
        ad.adb.shell(
        "setprop persist.vendor.sys.modem.diag.mdlog false", ignore_status=True)
        ad.adb.shell(
        "setprop persist.sys.modem.diag.mdlog false", ignore_status=True)
        disable_qxdm_logger(ad)
        cmds = ('am instrument -w -e request "WriteEFS" -e item '
                '"/google/pixel_multisim_config" -e data  "01 00 00 00" '
                '"com.google.mdstest/com.google.mdstest.instrument.'
                'ModemConfigInstrumentation"',
                'am instrument -w -e request "WriteEFS" -e item "/nv/item_files'
                '/modem/uim/uimdrv/uim_extended_slot_mapping_config" -e data '
                '"00 01 02 01" "com.google.mdstest/com.google.mdstest.'
                'instrument.ModemConfigInstrumentation"')
        for cmd in cmds:
            ad.log.info("Switch to SSIM mode by using %s", cmd)
            ad.adb.shell(cmd, ignore_status=True)
            time.sleep(timeout)
        ad.adb.shell("setprop persist.radio.multisim.config ssss")
        reboot_device(ad)
        # Verify if device is really in ssim mode
        mode = ad.droid.telephonyGetPhoneCount()
        if mode == 1:
            ad.log.info("Device correctly switched to SSIM mode")
            result = True
            break
        else:
            ad.log.warning("Attempt %d - failed to switch to SSIM", (i + 1))
    return result


def lock_lte_band_by_mds(ad, band):
    disable_qxdm_logger(ad)
    ad.log.info("Write band %s locking to efs file", band)
    if band == "4":
        item_string = (
            "4B 13 26 00 08 00 00 00 40 00 08 00 0B 00 08 00 00 00 00 00 00 00 "
            "2F 6E 76 2F 69 74 65 6D 5F 66 69 6C 65 73 2F 6D 6F 64 65 6D 2F 6D "
            "6D 6F 64 65 2F 6C 74 65 5F 62 61 6E 64 70 72 65 66 00")
    elif band == "13":
        item_string = (
            "4B 13 26 00 08 00 00 00 40 00 08 00 0A 00 00 10 00 00 00 00 00 00 "
            "2F 6E 76 2F 69 74 65 6D 5F 66 69 6C 65 73 2F 6D 6F 64 65 6D 2F 6D "
            "6D 6F 64 65 2F 6C 74 65 5F 62 61 6E 64 70 72 65 66 00")
    else:
        ad.log.error("Band %s is not supported", band)
        return False
    cmd = ('am instrument -w -e request "%s" com.google.mdstest/com.google.'
           'mdstest.instrument.ModemCommandInstrumentation')
    for _ in range(3):
        if "SUCCESS" in ad.adb.shell(cmd % item_string, ignore_status=True):
            break
    else:
        ad.log.error("Fail to write band by %s" % (cmd % item_string))
        return False

    # EFS Sync
    item_string = "4B 13 30 00 2A 00 2F 00"

    for _ in range(3):
        if "SUCCESS" in ad.adb.shell(cmd % item_string, ignore_status=True):
            break
    else:
        ad.log.error("Fail to sync efs by %s" % (cmd % item_string))
        return False
    time.sleep(5)
    reboot_device(ad)

def show_enhanced_4g_lte(ad, sub_id):
    result = True
    capabilities = ad.telephony["subscription"][sub_id].get("capabilities", [])
    if capabilities:
        if "hide_enhanced_4g_lte" in capabilities:
            result = False
            ad.log.info('"Enhanced 4G LTE MODE" is hidden for sub ID %s.', sub_id)
            show_enhanced_4g_lte_mode = getattr(ad, "show_enhanced_4g_lte_mode", False)
            if show_enhanced_4g_lte_mode in ["true", "True"]:
                current_voice_sub_id = get_outgoing_voice_sub_id(ad)
                if sub_id != current_voice_sub_id:
                    set_incoming_voice_sub_id(ad, sub_id)

                ad.log.info('Show "Enhanced 4G LTE MODE" forcibly for sub ID %s.', sub_id)
                ad.adb.shell("am broadcast -a com.google.android.carrier.action.LOCAL_OVERRIDE -n com.google.android.carrier/.ConfigOverridingReceiver --ez hide_enhanced_4g_lte_bool false")
                ad.telephony["subscription"][sub_id]["capabilities"].remove("hide_enhanced_4g_lte")

                if sub_id != current_voice_sub_id:
                    set_incoming_voice_sub_id(ad, current_voice_sub_id)

                result = True
    return result


def find_qxdm_log_mask(ad, mask="default.cfg"):
    """Find QXDM logger mask."""
    if "/" not in mask:
        # Call nexuslogger to generate log mask
        start_nexuslogger(ad)
        # Find the log mask path
        for path in (DEFAULT_QXDM_LOG_PATH, "/data/diag_logs",
                     "/vendor/etc/mdlog/"):
            out = ad.adb.shell(
                "find %s -type f -iname %s" % (path, mask), ignore_status=True)
            if out and "No such" not in out and "Permission denied" not in out:
                if path.startswith("/vendor/"):
                    setattr(ad, "qxdm_log_path", DEFAULT_QXDM_LOG_PATH)
                else:
                    setattr(ad, "qxdm_log_path", path)
                return out.split("\n")[0]
        if mask in ad.adb.shell("ls /vendor/etc/mdlog/"):
            setattr(ad, "qxdm_log_path", DEFAULT_QXDM_LOG_PATH)
            return "%s/%s" % ("/vendor/etc/mdlog/", mask)
    else:
        out = ad.adb.shell("ls %s" % mask, ignore_status=True)
        if out and "No such" not in out:
            qxdm_log_path, cfg_name = os.path.split(mask)
            setattr(ad, "qxdm_log_path", qxdm_log_path)
            return mask
    ad.log.warning("Could NOT find QXDM logger mask path for %s", mask)

def set_qxdm_logger_command(ad, mask=None):
    """Set QXDM logger always on.
    Args:
        ad: android device object.
    """
    ## Neet to check if log mask will be generated without starting nexus logger
    masks = []
    mask_path = None
    if mask:
        masks = [mask]
    masks.extend(["QC_Default.cfg", "default.cfg"])
    for mask in masks:
        mask_path = find_qxdm_log_mask(ad, mask)
        if mask_path: break
    if not mask_path:
        ad.log.error("Cannot find QXDM mask %s", mask)
        ad.qxdm_logger_command = None
        return False
    else:
        ad.log.info("Use QXDM log mask %s", mask_path)
        ad.log.debug("qxdm_log_path = %s", ad.qxdm_log_path)
        output_path = os.path.join(ad.qxdm_log_path, "logs")
        ad.qxdm_logger_command = ("diag_mdlog -f %s -o %s -s 90 -c" %
                                  (mask_path, output_path))
        for prop in ("persist.sys.modem.diag.mdlog",
                     "persist.vendor.sys.modem.diag.mdlog"):
            if ad.adb.getprop(prop):
                # Enable qxdm always on if supported
                for conf_path in ("/data/vendor/radio/diag_logs",
                                  "/vendor/etc/mdlog"):
                    if "diag.conf" in ad.adb.shell(
                            "ls %s" % conf_path, ignore_status=True):
                        conf_path = "%s/diag.conf" % conf_path
                        ad.adb.shell('echo "%s" > %s' %
                                     (ad.qxdm_logger_command, conf_path))
                        break
                ad.adb.shell("setprop %s true" % prop, ignore_status=True)
                break
        return True


def start_qxdm_logger(ad, begin_time=None):
    """Start QXDM logger."""
    if not getattr(ad, "qxdm_log", True): return
    # Delete existing QXDM logs 5 minutes earlier than the begin_time
    current_time = get_current_epoch_time()
    if getattr(ad, "qxdm_log_path", None):
        seconds = None
        file_count = ad.adb.shell(
            "find %s -type f -iname *.qmdl | wc -l" % ad.qxdm_log_path)
        if int(file_count) > 50:
            if begin_time:
                # if begin_time specified, delete old qxdm logs modified
                # 10 minutes before begin time
                seconds = int((current_time - begin_time) / 1000.0) + 10 * 60
            else:
                # if begin_time is not specified, delete old qxdm logs modified
                # 15 minutes before current time
                seconds = 15 * 60
        if seconds:
            # Remove qxdm logs modified more than specified seconds ago
            ad.adb.shell(
                "find %s -type f -iname *.qmdl -not -mtime -%ss -delete" %
                (ad.qxdm_log_path, seconds))
            ad.adb.shell(
                "find %s -type f -iname *.xml -not -mtime -%ss -delete" %
                (ad.qxdm_log_path, seconds))
    if getattr(ad, "qxdm_logger_command", None):
        output = ad.adb.shell("ps -ef | grep mdlog") or ""
        if ad.qxdm_logger_command not in output:
            ad.log.debug("QXDM logging command %s is not running",
                         ad.qxdm_logger_command)
            if "diag_mdlog" in output:
                # Kill the existing non-matching diag_mdlog process
                # Only one diag_mdlog process can be run
                stop_qxdm_logger(ad)
            ad.log.info("Start QXDM logger")
            ad.adb.shell_nb(ad.qxdm_logger_command)
            time.sleep(10)
        else:
            run_time = check_qxdm_logger_run_time(ad)
            if run_time < 600:
                # the last diag_mdlog started within 10 minutes ago
                # no need to restart
                return True
            if ad.search_logcat(
                    "Diag_Lib: diag: In delete_log",
                    begin_time=current_time -
                    run_time) or not ad.get_file_names(
                        ad.qxdm_log_path,
                        begin_time=current_time - 600000,
                        match_string="*.qmdl"):
                # diag_mdlog starts deleting files or no qmdl logs were
                # modified in the past 10 minutes
                ad.log.debug("Quit existing diag_mdlog and start a new one")
                stop_qxdm_logger(ad)
                ad.adb.shell_nb(ad.qxdm_logger_command)
                time.sleep(10)
        return True


def disable_qxdm_logger(ad):
    for prop in ("persist.sys.modem.diag.mdlog",
                 "persist.vendor.sys.modem.diag.mdlog",
                 "vendor.sys.modem.diag.mdlog_on"):
        if ad.adb.getprop(prop):
            ad.adb.shell("setprop %s false" % prop, ignore_status=True)
    for apk in ("com.android.nexuslogger", "com.android.pixellogger"):
        if ad.is_apk_installed(apk) and ad.is_apk_running(apk):
            ad.force_stop_apk(apk)
    stop_qxdm_logger(ad)
    return True


ef check_qxdm_logger_mask(ad, mask_file="QC_Default.cfg"):
    """Check if QXDM logger always on is set.
    Args:
        ad: android device object.
    """
    output = ad.adb.shell(
        "ls /data/vendor/radio/diag_logs/", ignore_status=True)
    if not output or "No such" in output:
        return True
    if mask_file not in ad.adb.shell(
            "cat /data/vendor/radio/diag_logs/diag.conf", ignore_status=True):
        return False
    return True


def send_dialer_secret_code(ad, secret_code):
    """Send dialer secret code.
    ad: android device controller
    secret_code: the secret code to be sent to dialer. the string between
                 code prefix *#*# and code postfix #*#*. *#*#<xxx>#*#*
    """
    action = 'android.provider.Telephony.SECRET_CODE'
    uri = 'android_secret_code://%s' % secret_code
    intent = ad.droid.makeIntent(
        action,
        uri,
        None,  # type
        None,  # extras
        None,  # categories,
        None,  # packagename,
        None,  # classname,
        0x01000000)  # flags
    ad.log.info('Issuing dialer secret dialer code: %s', secret_code)
    ad.droid.sendBroadcastIntent(intent)


def enable_radio_log_on(ad):
    if ad.adb.getprop("persist.vendor.radio.adb_log_on") != "1":
        ad.log.info("Enable radio adb_log_on and reboot")
        adb_disable_verity(ad)
        ad.adb.shell("setprop persist.vendor.radio.adb_log_on 1")
        reboot_device(ad)


def adb_disable_verity(ad):
    if ad.adb.getprop("ro.boot.veritymode") == "enforcing":
        ad.adb.disable_verity()
        reboot_device(ad)
        ad.adb.remount()

def set_preferred_apn_by_adb(ad, pref_apn_name):
    """Select Pref APN
       Set Preferred APN on UI using content query/insert
       It needs apn name as arg, and it will match with plmn id
    """
    try:
        plmn_id = get_plmn_by_adb(ad)
        out = ad.adb.shell("content query --uri content://telephony/carriers "
                           "--where \"apn='%s' and numeric='%s'\"" %
                           (pref_apn_name, plmn_id))
        if "No result found" in out:
            ad.log.warning("Cannot find APN %s on device", pref_apn_name)
            return False
        else:
            apn_id = re.search(r'_id=(\d+)', out).group(1)
            ad.log.info("APN ID is %s", apn_id)
            ad.adb.shell("content insert --uri content:"
                         "//telephony/carriers/preferapn --bind apn_id:i:%s" %
                         (apn_id))
            out = ad.adb.shell("content query --uri "
                               "content://telephony/carriers/preferapn")
            if "No result found" in out:
                ad.log.error("Failed to set prefer APN %s", pref_apn_name)
                return False
            elif apn_id == re.search(r'_id=(\d+)', out).group(1):
                ad.log.info("Preferred APN set to %s", pref_apn_name)
                return True
    except Exception as e:
        ad.log.error("Exception while setting pref apn %s", e)
        return True

def activate_esim_using_suw(ad):
    _START_SUW = ('am start -a android.intent.action.MAIN -n '
                  'com.google.android.setupwizard/.SetupWizardTestActivity')
    _STOP_SUW = ('am start -a com.android.setupwizard.EXIT')

    toggle_airplane_mode(ad.log, ad, new_state=False, strict_checking=False)
    ad.adb.shell("settings put system screen_off_timeout 1800000")
    ad.ensure_screen_on()
    ad.send_keycode("MENU")
    ad.send_keycode("HOME")
    for _ in range(3):
        ad.log.info("Attempt %d - activating eSIM", (_ + 1))
        ad.adb.shell(_START_SUW)
        time.sleep(10)
        log_screen_shot(ad, "start_suw")
        for _ in range(4):
            ad.send_keycode("TAB")
            time.sleep(0.5)
        ad.send_keycode("ENTER")
        time.sleep(15)
        log_screen_shot(ad, "activate_esim")
        get_screen_shot_log(ad)
        ad.adb.shell(_STOP_SUW)
        time.sleep(5)
        current_sim = get_sim_state(ad)
        ad.log.info("Current SIM status is %s", current_sim)
        if current_sim not in (SIM_STATE_ABSENT, SIM_STATE_UNKNOWN):
            break
    return True
