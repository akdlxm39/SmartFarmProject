# Modbus Register Map

| Register | Address | Name | Owner | Notes |
|---:|---:|---|---|---|
| 40021 | 20 | `conveyor_command` | PC vision/manual client | 0 stop, 1 cw, 2 ccw, 3 reset, 4 emergency_stop |
| 40022 | 21 | `conveyor_speed_cmd` | PC vision/manual client | 0 default, 1~100 speed scale |
| 40023 | 22 | `conveyor_status` | Raspberry Pi conveyor client | actual motor status |
| 40024 | 23 | `conveyor_error_code` | Raspberry Pi conveyor client | actual controller error |
| 40025 | 24 | `cube_detected` | PC vision client | 0/1 |
| 40026 | 25 | `cube_color` | PC vision client | 0 none, 1 red, 2 green, 3 unknown |
| 40027 | 26 | `last_vision_event` | PC vision client | 0 none, 1 detected, 2 lost, 3 delivered, 4 error, 5 estop |
| 40028 | 27 | `reserved_conveyor_1` | reserved | future conveyor heartbeat/sequence |
| 40029 | 28 | `reserved_conveyor_2` | reserved | future conveyor extension |
| 40030 | 29 | `reserved_conveyor_3` | reserved | future conveyor extension |
| 40031 | 30 | `dobot_command` | orchestrator/backend | 0 none, 1 home, 2 move_capture_pose, 3 pick, 4 place, 5 stop, 6 reset |
| 40032 | 31 | `dobot_target_slot` | orchestrator/backend | harvest slot or target index |
| 40033 | 32 | `dobot_command_seq` | orchestrator/backend | incrementing command sequence |
| 40034 | 33 | `dobot_command_ack_seq` | Dobot client | last handled command sequence |
| 40035 | 34 | `dobot_status` | Dobot client | 0 idle, 1 moving, 2 capturing, 3 picking, 4 placing, 5 paused, 6 error |
| 40036 | 35 | `dobot_error_code` | Dobot client | Dobot/ROS error code |
| 40037 | 36 | `dobot_current_step` | Dobot client | harvest/capture/place sequence step |
| 40038 | 37 | `dobot_quality_result` | Dobot/AI client | 0 unknown, 1 good, 2 bad |
| 40039 | 38 | `dobot_busy` | Dobot client | 0/1 |
| 40040 | 39 | `dobot_heartbeat` | Dobot client | incrementing heartbeat |
| 40041 | 40 | `dobot_last_event` | Dobot client | last Dobot event enum |
| 40051 | 50 | `turtlebot_command` | orchestrator/backend | 0 none, 1 deliver_start, 2 pause, 3 resume, 4 return_home, 5 stop, 6 reset |
| 40052 | 51 | `turtlebot_target_goal` | orchestrator/backend | delivery destination/goal index |
| 40053 | 52 | `turtlebot_command_seq` | orchestrator/backend | incrementing command sequence |
| 40054 | 53 | `turtlebot_command_ack_seq` | TurtleBot client | last handled command sequence |
| 40055 | 54 | `turtlebot_status` | TurtleBot client | 0 idle, 1 navigating, 2 arrived, 3 delivering, 4 paused, 5 error |
| 40056 | 55 | `turtlebot_error_code` | TurtleBot client | navigation/ROS error code |
| 40057 | 56 | `turtlebot_nav_state` | TurtleBot client | Nav2/internal navigation state |
| 40058 | 57 | `turtlebot_battery_percent` | TurtleBot client | 0~100 |
| 40059 | 58 | `turtlebot_current_goal` | TurtleBot client | current goal index |
| 40060 | 59 | `turtlebot_delivery_count_lo` | TurtleBot client | device delivery count low 16 bits |
| 40061 | 60 | `turtlebot_delivery_count_hi` | TurtleBot client | device delivery count high 16 bits |
| 40062 | 61 | `turtlebot_last_event` | TurtleBot client | last TurtleBot event enum |
| 40063 | 62 | `turtlebot_heartbeat` | TurtleBot client | incrementing heartbeat |
| 40071 | 70 | `system_command` | Web/backend | 0 none, 1 harvest_start, 2 pause_all, 3 resume_all |
| 40072 | 71 | `system_command_seq` | Web/backend | increment to issue a new system command |
| 40073 | 72 | `system_command_ack_seq` | orchestrator/backend | last handled system command sequence |
| 40074 | 73 | `system_state` | orchestrator/backend | 0 idle, 1 harvesting, 2 paused, 3 error, 4 emergency_stop |
| 40075 | 74 | `system_error_code` | orchestrator/backend | overall system error code |
| 40076 | 75 | `ai_defect_rate_bp` | AI/backend | basis points: 0~10000 = 0.00%~100.00% |
| 40077 | 76 | `total_harvest_count_lo` | backend/stat aggregator | total harvest count low 16 bits |
| 40078 | 77 | `total_harvest_count_hi` | backend/stat aggregator | total harvest count high 16 bits |
| 40079 | 78 | `turtlebot_delivery_total_lo` | backend/stat aggregator | TurtleBot total deliveries low 16 bits |
| 40080 | 79 | `turtlebot_delivery_total_hi` | backend/stat aggregator | TurtleBot total deliveries high 16 bits |
| 40081 | 80 | `tomato_good_count_lo` | backend/stat aggregator | tomato good count low 16 bits |
| 40082 | 81 | `tomato_good_count_hi` | backend/stat aggregator | tomato good count high 16 bits |
| 40083 | 82 | `tomato_bad_count_lo` | backend/stat aggregator | tomato bad count low 16 bits |
| 40084 | 83 | `tomato_bad_count_hi` | backend/stat aggregator | tomato bad count high 16 bits |
| 40085 | 84 | `carrot_good_count_lo` | backend/stat aggregator | carrot good count low 16 bits |
| 40086 | 85 | `carrot_good_count_hi` | backend/stat aggregator | carrot good count high 16 bits |
| 40087 | 86 | `carrot_bad_count_lo` | backend/stat aggregator | carrot bad count low 16 bits |
| 40088 | 87 | `carrot_bad_count_hi` | backend/stat aggregator | carrot bad count high 16 bits |
| 40089 | 88 | `radish_good_count_lo` | backend/stat aggregator | radish good count low 16 bits |
| 40090 | 89 | `radish_good_count_hi` | backend/stat aggregator | radish good count high 16 bits |
| 40091 | 90 | `radish_bad_count_lo` | backend/stat aggregator | radish bad count low 16 bits |
| 40092 | 91 | `radish_bad_count_hi` | backend/stat aggregator | radish bad count high 16 bits |
| 40093 | 92 | `farm_stats_seq` | backend/stat aggregator | incrementing stats update sequence |
| 40094 | 93 | `farm_heartbeat` | backend/stat aggregator | farm stats heartbeat |
