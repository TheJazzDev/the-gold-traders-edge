Starting Container
2025-12-24 22:18:22,597 INFO spawned: 'api' with pid 2
2025-12-24 22:18:22,598 INFO spawned: 'signal-generator' with pid 3
2025-12-24 22:18:22,598 INFO spawned: 'signal-generator' with pid 3
2025-12-24 22:18:21,593 CRIT Supervisor is running as root.  Privileges were not dropped because no user is specified in the config file.  If you intend to run as root, you can set user=root in the config file to avoid this message.
2025-12-24 22:18:21,593 CRIT Supervisor is running as root.  Privileges were not dropped because no user is specified in the config file.  If you intend to run as root, you can set user=root in the config file to avoid this message.
2025-12-24 22:18:21,594 INFO supervisord started with pid 1
2025-12-24 22:18:21,594 INFO supervisord started with pid 1
2025-12-24 22:18:22,597 INFO spawned: 'api' with pid 2
2025-12-24 22:18:23,392 - __main__ - INFO - 🚀 Initializing 5m generator...
2025-12-24 22:18:23,392 - __main__ - INFO - ✅ Started worker for 5m
2025-12-24 22:18:23,392 - __main__ - INFO -    [5m] All 5 profitable rules enabled: ['momentum_equilibrium', 'london_session_breakout', 'golden_fibonacci', 'ath_retest', 'order_block_retest']
INFO:     Started server process [2]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
AttributeError: 'DatabaseSubscriber' object has no attribute 'on_signal'
2025-12-24 22:18:23,697 - __main__ - ERROR - ❌ [5m] Worker failed: 'DatabaseSubscriber' object has no attribute 'on_signal'
Traceback (most recent call last):
  File "/app/engine/run_multi_timeframe_service.py", line 126, in _run
    self.generator.add_subscriber(db_subscriber.on_signal)
                                  ^^^^^^^^^^^^^^^^^^^^^^^
2025-12-24 22:18:23,697 - signals.subscribers.database_subscriber - INFO - ✅ DatabaseSubscriber initialized: postgresql://postgres:WuOXHUmfceYvlbNuyUrhAsQgJPmFyhJv@postgres.railway.internal:5432/railway
2025-12-24 22:18:23,697 INFO success: api entered RUNNING state, process has stayed up for > than 1 seconds (startsecs)
2025-12-24 22:18:23,697 INFO success: api entered RUNNING state, process has stayed up for > than 1 seconds (startsecs)
2025-12-24 22:18:25,392 - __main__ - INFO - 🚀 Initializing 15m generator...
2025-12-24 22:18:25,393 - __main__ - INFO - ✅ Started worker for 15m
2025-12-24 22:18:25,393 - __main__ - INFO -    [15m] All 5 profitable rules enabled: ['momentum_equilibrium', 'london_session_breakout', 'golden_fibonacci', 'ath_retest', 'order_block_retest']
2025-12-24 22:18:25,559 - signals.subscribers.database_subscriber - INFO - ✅ DatabaseSubscriber initialized: postgresql://postgres:WuOXHUmfceYvlbNuyUrhAsQgJPmFyhJv@postgres.railway.internal:5432/railway
2025-12-24 22:18:25,559 - __main__ - ERROR - ❌ [15m] Worker failed: 'DatabaseSubscriber' object has no attribute 'on_signal'
Traceback (most recent call last):
  File "/app/engine/run_multi_timeframe_service.py", line 126, in _run
    self.generator.add_subscriber(db_subscriber.on_signal)
                                  ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'DatabaseSubscriber' object has no attribute 'on_signal'
2025-12-24 22:18:27,393 - __main__ - INFO - 🚀 Initializing 30m generator...
2025-12-24 22:18:27,394 - __main__ - INFO - ✅ Started worker for 30m
2025-12-24 22:18:27,394 - __main__ - INFO -    [30m] All 5 profitable rules enabled: ['momentum_equilibrium', 'london_session_breakout', 'golden_fibonacci', 'ath_retest', 'order_block_retest']
2025-12-24 22:18:27,686 - signals.subscribers.database_subscriber - INFO - ✅ DatabaseSubscriber initialized: postgresql://postgres:WuOXHUmfceYvlbNuyUrhAsQgJPmFyhJv@postgres.railway.internal:5432/railway
2025-12-24 22:18:27,686 - __main__ - ERROR - ❌ [30m] Worker failed: 'DatabaseSubscriber' object has no attribute 'on_signal'
Traceback (most recent call last):
  File "/app/engine/run_multi_timeframe_service.py", line 126, in _run
    self.generator.add_subscriber(db_subscriber.on_signal)
                                  ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'DatabaseSubscriber' object has no attribute 'on_signal'
2025-12-24 22:18:29,394 - __main__ - INFO - 🚀 Initializing 1h generator...
2025-12-24 22:18:29,394 - __main__ - INFO - ✅ Started worker for 1h
2025-12-24 22:18:29,394 - __main__ - INFO -    [1h] All 5 profitable rules enabled: ['momentum_equilibrium', 'london_session_breakout', 'golden_fibonacci', 'ath_retest', 'order_block_retest']
2025-12-24 22:18:29,525 - signals.subscribers.database_subscriber - INFO - ✅ DatabaseSubscriber initialized: postgresql://postgres:WuOXHUmfceYvlbNuyUrhAsQgJPmFyhJv@postgres.railway.internal:5432/railway
2025-12-24 22:18:29,526 - __main__ - ERROR - ❌ [1h] Worker failed: 'DatabaseSubscriber' object has no attribute 'on_signal'
Traceback (most recent call last):
  File "/app/engine/run_multi_timeframe_service.py", line 126, in _run
    self.generator.add_subscriber(db_subscriber.on_signal)
                                  ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'DatabaseSubscriber' object has no attribute 'on_signal'
2025-12-24 22:18:31,395 - __main__ - INFO - 🚀 Initializing 4h generator...
2025-12-24 22:18:31,395 - __main__ - INFO - ✅ Started worker for 4h
2025-12-24 22:18:31,395 - __main__ - INFO -    [4h] All 5 profitable rules enabled: ['momentum_equilibrium', 'london_session_breakout', 'golden_fibonacci', 'ath_retest', 'order_block_retest']
2025-12-24 22:18:31,663 - signals.subscribers.database_subscriber - INFO - ✅ DatabaseSubscriber initialized: postgresql://postgres:WuOXHUmfceYvlbNuyUrhAsQgJPmFyhJv@postgres.railway.internal:5432/railway
2025-12-24 22:18:31,664 - __main__ - ERROR - ❌ [4h] Worker failed: 'DatabaseSubscriber' object has no attribute 'on_signal'
Traceback (most recent call last):
  File "/app/engine/run_multi_timeframe_service.py", line 126, in _run
    self.generator.add_subscriber(db_subscriber.on_signal)
                                  ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'DatabaseSubscriber' object has no attribute 'on_signal'
2025-12-24 22:18:32,665 INFO success: signal-generator entered RUNNING state, process has stayed up for > than 10 seconds (startsecs)
2025-12-24 22:18:32,665 INFO success: signal-generator entered RUNNING state, process has stayed up for > than 10 seconds (startsecs)
2025-12-24 22:18:33,396 - __main__ - INFO - 🚀 Initializing 1d generator...
2025-12-24 22:18:33,396 - __main__ - INFO - ✅ Started worker for 1d
2025-12-24 22:18:33,396 - __main__ - INFO -    [1d] All 5 profitable rules enabled: ['momentum_equilibrium', 'london_session_breakout', 'golden_fibonacci', 'ath_retest', 'order_block_retest']
2025-12-24 22:18:33,523 - signals.subscribers.database_subscriber - INFO - ✅ DatabaseSubscriber initialized: postgresql://postgres:WuOXHUmfceYvlbNuyUrhAsQgJPmFyhJv@postgres.railway.internal:5432/railway
2025-12-24 22:18:33,523 - __main__ - ERROR - ❌ [1d] Worker failed: 'DatabaseSubscriber' object has no attribute 'on_signal'
Traceback (most recent call last):
  File "/app/engine/run_multi_timeframe_service.py", line 126, in _run
    self.generator.add_subscriber(db_subscriber.on_signal)
                                  ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'DatabaseSubscriber' object has no attribute 'on_signal'
2025-12-24 22:18:35,396 - __main__ - INFO - 🎉 All 6 workers started successfully
2025-12-24 22:18:45,397 - __main__ - WARNING - ⚠️  Worker 5m has stopped, restarting...
2025-12-24 22:18:45,397 - __main__ - WARNING - ⚠️  Worker 15m has stopped, restarting...
2025-12-24 22:18:45,397 - __main__ - WARNING - ⚠️  Worker 30m has stopped, restarting...
2025-12-24 22:18:45,397 - __main__ - WARNING - ⚠️  Worker 1h has stopped, restarting...
2025-12-24 22:18:45,397 - __main__ - WARNING - ⚠️  Worker 4h has stopped, restarting...
2025-12-24 22:18:45,397 - __main__ - WARNING - ⚠️  Worker 1d has stopped, restarting...
2025-12-24 22:19:05,398 - __main__ - WARNING - ⚠️  Worker 15m has stopped, restarting...
2025-12-24 22:19:05,398 - __main__ - WARNING - ⚠️  Worker 30m has stopped, restarting...
2025-12-24 22:19:05,398 - __main__ - WARNING - ⚠️  Worker 1h has stopped, restarting...
2025-12-24 22:19:05,398 - __main__ - WARNING - ⚠️  Worker 4h has stopped, restarting...
2025-12-24 22:19:05,398 - __main__ - WARNING - ⚠️  Worker 1d has stopped, restarting...
2025-12-24 22:18:55,397 - __main__ - WARNING - ⚠️  Worker 5m has stopped, restarting...
2025-12-24 22:18:55,397 - __main__ - WARNING - ⚠️  Worker 15m has stopped, restarting...
2025-12-24 22:18:55,397 - __main__ - WARNING - ⚠️  Worker 30m has stopped, restarting...
2025-12-24 22:18:55,397 - __main__ - WARNING - ⚠️  Worker 1h has stopped, restarting...
2025-12-24 22:18:55,397 - __main__ - WARNING - ⚠️  Worker 4h has stopped, restarting...
2025-12-24 22:18:55,397 - __main__ - WARNING - ⚠️  Worker 1d has stopped, restarting...
2025-12-24 22:19:05,397 - __main__ - WARNING - ⚠️  Worker 5m has stopped, restarting...
2025-12-24 22:19:15,398 - __main__ - WARNING - ⚠️  Worker 5m has stopped, restarting...
2025-12-24 22:19:15,398 - __main__ - WARNING - ⚠️  Worker 15m has stopped, restarting...
2025-12-24 22:19:15,398 - __main__ - WARNING - ⚠️  Worker 30m has stopped, restarting...
2025-12-24 22:19:15,398 - __main__ - WARNING - ⚠️  Worker 1h has stopped, restarting...
2025-12-24 22:19:15,398 - __main__ - WARNING - ⚠️  Worker 4h has stopped, restarting...
2025-12-24 22:19:15,398 - __main__ - WARNING - ⚠️  Worker 1d has stopped, restarting...