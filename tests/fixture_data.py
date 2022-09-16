users = [
    {
        "name": "john doe",
        "id": "abc123",
        "email": "john@example.com",
        "role": "manager",
        "description": "who am i",
    },
    {
        "name": "jane",
        "id": "xyz789",
        "email": "jane@example.com",
        "role": "user",
        "description": "",
    },
]

user_john = {
    "id": "abc123",
    "firstName": "john",
    "lastName": "doe",
    "emailAddress": "john@example.com",
    "role": "manager",
    "bio": "who am i",
}
user_jane = {
    "id": "xyz789",
    "firstName": "jane",
    "lastName": "jane",
    "emailAddress": "jane@example.com",
    "role": "user",
    "bio": "",
}

lir_user_john = {
    "firstName": "john",
    "lastName": "doe",
    "emailAddress": "john@example.com",
    "role": "manager",
    "bio": "who am i",
}
lir_user_jane = {
    "firstName": "jane",
    "lastName": "jane",
    "emailAddress": "jane@example.com",
    "role": "user",
    "bio": "",
}

pd_user_list = [user_john, user_jane]

teams = [
    {"id": "abc123", "name": "test team 1", "description": "a fabulous team"},
    {"id": "xyz789", "name": "test team 2", "description": "a decent team"},
]

pd_teams = [
    {
        "id": "tabc123",
        "name": "test team 1",
        "description": "a fabulous team",
        "members": ["abc123", "xyz789"],
        "manager": "xyz789",
    },
    {
        "id": "txyz789",
        "name": "test team 2",
        "description": "a decent team",
        "members": ["abc123"],
        "manager": "abc123",
    },
]

pd_team_members = {
    "tabc123": {"members": ["abc123", "xyz789"], "manager": "xyz789"},
    "txyz789": {"members": ["abc123"], "manager": "abc123"},
}

mapper_teams = {"abc123": {"sysId": "sysIdabc123"}, "xyz789": {"sysId": "sysIdxyz789"}}


services = [
    {
        "id": "abc123",
        "description": "foobar",
        "teams": [{"id": "abc123", "name": "team1"}],
        "name": "important service",
    },
    {
        "id": "xyz789",
        "description": "fizzbuzz",
        "teams": [{"id": "abc123", "name": "team1"}],
        "name": "another important service",
    },
]

services_no_teams = [
    {
        "id": "abc123",
        "description": "foobar",
        "teams": [],
        "name": "important service",
    },
    {
        "id": "xyz789",
        "description": "fizzbuzz",
        "teams": [],
        "name": "another important service",
    },
]

schedule_details = {
    "schedule_layers": [
        {
            "name": "Layer 1",
            "rendered_schedule_entries": [
                {
                    "start": "2015-11-09T08:00:00-05:00",
                    "end": "2015-11-09T17:00:00-05:00",
                    "user": {
                        "id": "abc123",
                        "type": "user_reference",
                    },
                }
            ],
            "start": "2015-11-06T21:00:00-05:00",
            "end": None,
            "rotation_turn_length_seconds": 86400,
            "users": [
                {
                    "user": {
                        "id": "abc123",
                    }
                }
            ],
        }
    ],
    "teams": teams[0],
}

schedules = [
    {
        "name": "test schedule 0",
        "id": "abc123",
        "timeZone": "America/New_York",
        "time_zone": "America/New_York",
        "users": users,
        "teams": [],
        "schedule_layers": schedule_details["schedule_layers"],
        "primaryMembers": ["abc123", "xyz789"],
    },
    {
        "name": "test schedule 1",
        "id": "abc123",
        "timeZone": "America/New_York",
        "time_zone": "America/New_York",
        "users": users,
        "teams": [],
        "schedule_layers": schedule_details["schedule_layers"],
        "primaryMembers": ["abc123", "xyz789"],
    },
    {
        "name": "test schedule 2",
        "id": "xyz789",
        "timeZone": "America/New_York",
        "time_zone": "America/New_York",
        "users": users,
        "teams": [{"id": "txyz789"}],
        "schedule_layers": schedule_details["schedule_layers"],
    },
    {
        "name": "test schedule 3",
        "id": "qwe456",
        "timeZone": "America/New_York",
        "time_zone": "America/New_York",
        "users": [],
        "teams": [],
        "schedule_layers": schedule_details["schedule_layers"],
    },
]

rendered_schedule = {
    "name": "test schedule 1",
    "id": "abc123",
    "timeZone": "America/New_York",
    "primaryMembers": ["abc123", "xyz789"],
    "schedule_layers": schedule_details["schedule_layers"],
    "teams": teams[0],
}

rendered_shifts = {
    "abc123": [
        {
            "name": "test schedule 1 (test schedule 1 (schedule based team)) - layer 0",
            "team": "sysIdabc123",
            "startTime": "21:00",
            "startDate": "2015-11-06",
            "endTime": "09:00",
            "repeatUntil": "2020-11-06",
            "rotationType": "daily",
            "timeZone": "America/New_York",
            "primaryMembers": ["abc123"],
            "backupMembers": [],
        }
    ],
    "xyz789": [
        {
            "name": "test schedule 2 (test team 2) - layer 0",
            "team": "sysIdtxyz789",
            "startTime": "21:00",
            "startDate": "2015-11-06",
            "endTime": "09:00",
            "repeatUntil": "2020-11-06",
            "rotationType": "daily",
            "timeZone": "America/New_York",
            "primaryMembers": ["abc123"],
            "backupMembers": [],
        }
    ],
}

team_from_escalation = {
    "escalation_rules": [
        {
            "id": "PGHDV41",
            "escalation_delay_in_minutes": 30,
            "targets": [
                {
                    "id": "abc123",
                    "type": "user_reference",
                }
            ],
        }
    ],
    "name": "test team policy (service based team)",
}

escalations = [
    {
        "id": "abc123",
        "escalation_rules": [
            {
                "id": "PGHDV41",
                "escalation_delay_in_minutes": 30,
                "targets": [
                    {"id": "abc123", "type": "user_reference"},
                    {
                        "id": "xyz789",
                        "type": "schedule_reference",
                    },
                    {"id": "abc123", "type": "fake_type"},
                ],
            }
        ],
        "teams": teams,
        "name": "escalation policy test",
    },
    {
        "id": "xyz789",
        "escalation_rules": [
            {
                "id": "PGHDV41",
                "escalation_delay_in_minutes": 30,
                "targets": [
                    {"id": "abc123", "type": "user_reference"},
                    {
                        "id": "xyz789",
                        "type": "schedule_reference",
                    },
                ],
            }
        ],
        "teams": [],
        "name": "escalation policy test no team",
    },
    {
        "id": "xyz789",
        "escalation_rules": [
            {
                "id": "PGHDV41",
                "escalation_delay_in_minutes": 30,
                "targets": [
                    {"id": "abc123", "type": "user_reference"},
                ],
            }
        ],
        "teams": teams,
        "name": "escalation policy test no audience",
    },
    {
        "id": "xyz789noaudience",
        "escalation_rules": [
            {"id": "PGHDV41", "escalation_delay_in_minutes": 30, "targets": []}
        ],
        "teams": teams,
        "name": "escalation policy test no audience",
    },
]

rendered_escalation = [
    {
        "id": "abc123",
        "rules": [
            {
                "id": "PGHDV41",
                "escalation_delay_in_minutes": 30,
                "targets": [
                    {"id": "abc123", "type": "user_reference"},
                    {"id": "xyz789", "type": "schedule_reference"},
                    {"id": "abc123", "type": "fake_type"},
                ],
            }
        ],
        "teams": [
            {"id": "abc123", "name": "test team 1", "description": "a fabulous team"},
            {"id": "xyz789", "name": "test team 2", "description": "a decent team"},
        ],
        "name": "escalation policy test",
    },
    {
        "id": "xyz789",
        "rules": [
            {
                "id": "PGHDV41",
                "escalation_delay_in_minutes": 30,
                "targets": [
                    {"id": "abc123", "type": "user_reference"},
                    {"id": "xyz789", "type": "schedule_reference"},
                ],
            }
        ],
        "teams": [],
        "name": "escalation policy test no team",
    },
    {
        "id": "xyz789",
        "rules": [
            {
                "id": "PGHDV41",
                "escalation_delay_in_minutes": 30,
                "targets": [{"id": "abc123", "type": "user_reference"}],
            }
        ],
        "teams": teams,
        "name": "escalation policy test no audience",
    },
    {
        "id": "xyz789noaudience",
        "rules": [{"id": "PGHDV41", "escalation_delay_in_minutes": 30, "targets": []}],
        "teams": teams,
        "name": "escalation policy test no audience",
    },
]
