"""
endpoint_config.py

Master configuration for SKY API → BigQuery pipeline.

===========================================================================
HOW TO USE:
  - SCHEMAS is a list of API schemas. Each schema maps to one BigQuery dataset.
  - To ENABLE  an entire API: uncomment its schema dict below.
  - To DISABLE an entire API: comment out its schema dict with #.

  - Within each schema, the "endpoints" list works the same as before:
      - To ENABLE  an endpoint: uncomment its dict entry.
      - To DISABLE an endpoint: comment out its dict entry with #.

  - The pipeline will only process schemas and endpoints that are active.
===========================================================================

Each schema entry has:
    api_name   (str)  : Human-readable label for logs.
    base_url   (str)  : The root URL for this API (paths are appended to it).
    bq_dataset (str)  : Target BigQuery dataset name.
    endpoints  (list) : List of endpoint dicts (same format as before).

Each endpoint entry has:
    path            (str)  : The API path (appended to the schema's base_url).
    bq_table        (str)  : Target BigQuery table name in the dataset.
    description     (str)  : Human-readable label (for logs).
    flatten_fields  (list) : Nested object keys to flatten into prefixed columns.
    required_params (dict) : Required query parameters. Leave as {} if none.
"""

# ---------------------------------------------------------------------------
# Master Schema + Endpoint List
# ---------------------------------------------------------------------------
# Comment or uncomment schemas and endpoints to control which data is synced.
# ---------------------------------------------------------------------------

SCHEMAS = [

    # ===================================================================
    # SCHOOL API
    # ===================================================================
    {
        "api_name": "School",
        "base_url": "https://api.sky.blackbaud.com/school",
        "bq_dataset": "bbem_school",
        "endpoints": [

            # ---------------------------------------------------------------
            # CORE ENDPOINTS
            # ---------------------------------------------------------------

            {
                "path": "/v1/levels",
                "bq_table": "core_school_levels",
                "description": "Core school levels",
                "flatten_fields": ["address", "school_address"],
                "required_params": {},
            },

            # {
            #     "path": "/v1/roles",
            #     "bq_table": "core_roles",
            #     "description": "Core roles",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/years",
            #     "bq_table": "core_years",
            #     "description": "Core school years",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/gradelevels",
            #     "bq_table": "core_grade_levels",
            #     "description": "Core grade levels",
            #     "flatten_fields": ["promotion"],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/offeringtypes",
            #     "bq_table": "core_offering_types",
            #     "description": "Core offering types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/terms",
            #     "bq_table": "core_terms",
            #     "description": "Core terms",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/timezone",
            #     "bq_table": "core_timezone",
            #     "description": "Core time zone",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/sessions",
            #     "bq_table": "core_sessions",
            #     "description": "Core sessions",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/customfields",
            #     "bq_table": "core_custom_fields",
            #     "description": "Core custom fields",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # USER ENDPOINTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/users",
            #     "bq_table": "users",
            #     "description": "Users by role(s)",
            #     "flatten_fields": [],
            #     "required_params": {"roles": "ALL_ROLE_IDS"},
            # },

            # {
            #     "path": "/v1/users/extended",
            #     "bq_table": "users_extended",
            #     "description": "Users extended by role(s)",
            #     "flatten_fields": [],
            #     "required_params": {"base_role_ids": "ALL_ROLE_IDS"},
            # },

            # {
            #     "path": "/v1/users/changed",
            #     "bq_table": "users_changed",
            #     "description": "Users changed by base role(s)",
            #     "flatten_fields": [],
            #     "required_params": {"base_role_ids": "ALL_ROLE_IDS"},
            # },

            # {
            #     "path": "/v1/users/enrollments",
            #     "bq_table": "users_enrollments",
            #     "description": "Users enrollments by year",
            #     "flatten_fields": [],
            #     "required_params": {"school_year": "2025-2026"},
            # },

            # {
            #     "path": "/v1/users/audit",
            #     "bq_table": "users_audit",
            #     "description": "Users audit by role ID",
            #     "flatten_fields": [],
            #     "required_params": {"role_id": "YOUR_ROLE_ID"},
            # },

            # {
            #     "path": "/v1/users/phonetypes",
            #     "bq_table": "users_phone_types",
            #     "description": "Users phone types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/users/addresstypes",
            #     "bq_table": "users_address_types",
            #     "description": "Users address types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/users/gendertypes",
            #     "bq_table": "users_gender_types",
            #     "description": "Users gender types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/users/bbidstatus",
            #     "bq_table": "users_bbid_status",
            #     "description": "Users BBID status by role(s)",
            #     "flatten_fields": [],
            #     "required_params": {"roles": "ALL_ROLE_IDS"},
            # },

            # {
            #     "path": "/v1/users/employment",
            #     "bq_table": "users_employment",
            #     "description": "Users employment by role(s)",
            #     "flatten_fields": [],
            #     "required_params": {"roles": "ALL_ROLE_IDS"},
            # },

            # {
            #     "path": "/v1/users/emergencycontacts/changed",
            #     "bq_table": "users_emergency_contacts_changed",
            #     "description": "Users emergency contact changes",
            #     "flatten_fields": [],
            #     "required_params": {"start_date": "2025-01-01"},
            # },

            # {
            #     "path": "/v1/users/me",
            #     "bq_table": "users_me",
            #     "description": "Current authenticated user",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/users/customfields",
            #     "bq_table": "users_custom_fields",
            #     "description": "Users custom fields list by base role(s)",
            #     "flatten_fields": [],
            #     "required_params": {"base_role_ids": "ALL_ROLE_IDS"},
            # },

            # ---------------------------------------------------------------
            # ACADEMICS ENDPOINTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/academics/sections",
            #     "bq_table": "academics_sections",
            #     "description": "Academics sections by school level",
            #     "flatten_fields": [],
            #     "required_params": {"level_num": "YOUR_LEVEL_ID"},
            # },

            # {
            #     "path": "/v1/academics/sections/students",
            #     "bq_table": "academics_sections_students",
            #     "description": "Academics sections students",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/academics/departments",
            #     "bq_table": "academics_departments",
            #     "description": "Academics departments",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/academics/courses",
            #     "bq_table": "academics_courses",
            #     "description": "Academics courses",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/academics/specialdays",
            #     "bq_table": "academics_special_days",
            #     "description": "Academics special days",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/academics/schedules/sets",
            #     "bq_table": "academics_schedule_sets",
            #     "description": "Academics schedule sets by level",
            #     "flatten_fields": [],
            #     "required_params": {"level_num": "YOUR_LEVEL_ID"},
            # },

            # {
            #     "path": "/v1/academics/schedules/master",
            #     "bq_table": "academics_master_schedule",
            #     "description": "Academics master schedule",
            #     "flatten_fields": [],
            #     "required_params": {"level_num": "YOUR_LEVEL_ID", "school_year": "2025-2026"},
            # },

            # {
            #     "path": "/v1/academics/enrollments/changes",
            #     "bq_table": "academics_enrollment_changes",
            #     "description": "Academics student enrollments changes",
            #     "flatten_fields": [],
            #     "required_params": {"start_date": "2025-01-01"},
            # },

            # {
            #     "path": "/v1/academics/rosters",
            #     "bq_table": "academics_rosters",
            #     "description": "Academics rosters",
            #     "flatten_fields": [],
            #     "required_params": {"section_ids": "YOUR_SECTION_IDS"},
            # },

            # {
            #     "path": "/v1/academics/courserequests",
            #     "bq_table": "academics_course_requests",
            #     "description": "Academics course requests",
            #     "flatten_fields": [],
            #     "required_params": {"school_year": "2025-2026"},
            # },

            # ---------------------------------------------------------------
            # ATHLETICS ENDPOINTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/athletics/sports",
            #     "bq_table": "athletics_sports",
            #     "description": "Athletics sports",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/athletics/teams",
            #     "bq_table": "athletics_teams",
            #     "description": "Athletics teams",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/athletics/schedules",
            #     "bq_table": "athletics_schedules",
            #     "description": "Athletics schedules",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/athletics/sportslevels",
            #     "bq_table": "athletics_sports_levels",
            #     "description": "Athletics sports levels",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/athletics/venues",
            #     "bq_table": "athletics_venues",
            #     "description": "Athletics venues",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/athletics/transportationtypes",
            #     "bq_table": "athletics_transportation_types",
            #     "description": "Athletics transportation types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/athletics/locations",
            #     "bq_table": "athletics_locations",
            #     "description": "Athletics locations",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/athletics/opponents",
            #     "bq_table": "athletics_opponents",
            #     "description": "Athletics opponents",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/athletics/rosters",
            #     "bq_table": "athletics_rosters",
            #     "description": "Athletics rosters",
            #     "flatten_fields": [],
            #     "required_params": {"section_ids": "YOUR_SECTION_IDS"},
            # },

            # ---------------------------------------------------------------
            # ATTENDANCE ENDPOINTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/attendance",
            #     "bq_table": "attendance",
            #     "description": "Attendance record",
            #     "flatten_fields": [],
            #     "required_params": {"level_id": "YOUR_LEVEL_ID"},
            # },

            # ---------------------------------------------------------------
            # ADMISSIONS ENDPOINTS (Legacy)
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/admissions/candidates",
            #     "bq_table": "admissions_candidates",
            #     "description": "Admissions candidates (Legacy)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/admissions/status",
            #     "bq_table": "admissions_statuses",
            #     "description": "Admissions statuses (Legacy)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/admissions/checklists",
            #     "bq_table": "admissions_checklists",
            #     "description": "Admissions checklists (Legacy)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/admissions/checkliststatus",
            #     "bq_table": "admissions_checklist_status",
            #     "description": "Admissions checklist status (Legacy)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # ADVISORIES ENDPOINTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/advisories/sections",
            #     "bq_table": "advisories_sections",
            #     "description": "Advisories sections by school level",
            #     "flatten_fields": [],
            #     "required_params": {"level_num": "YOUR_LEVEL_ID"},
            # },

            # {
            #     "path": "/v1/advisories/rosters",
            #     "bq_table": "advisories_rosters",
            #     "description": "Advisories rosters",
            #     "flatten_fields": [],
            #     "required_params": {"section_ids": "YOUR_SECTION_IDS"},
            # },

            # ---------------------------------------------------------------
            # ACTIVITIES ENDPOINTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/activities/sections",
            #     "bq_table": "activities_sections",
            #     "description": "Activities sections by school level",
            #     "flatten_fields": [],
            #     "required_params": {"level_num": "YOUR_LEVEL_ID"},
            # },

            # {
            #     "path": "/v1/activities/rosters",
            #     "bq_table": "activities_rosters",
            #     "description": "Activities rosters",
            #     "flatten_fields": [],
            #     "required_params": {"section_ids": "YOUR_SECTION_IDS"},
            # },

            # ---------------------------------------------------------------
            # DORMS ENDPOINTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/dorms/all",
            #     "bq_table": "dorms",
            #     "description": "Dorms by school level",
            #     "flatten_fields": [],
            #     "required_params": {"level_num": "YOUR_LEVEL_ID"},
            # },

            # {
            #     "path": "/v1/dorms/rosters",
            #     "bq_table": "dorms_rosters",
            #     "description": "Dorms rosters",
            #     "flatten_fields": [],
            #     "required_params": {"section_ids": "YOUR_SECTION_IDS"},
            # },

            # ---------------------------------------------------------------
            # VENUES / BUILDINGS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/venues/buildings",
            #     "bq_table": "venues_buildings",
            #     "description": "Core buildings",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # LISTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/lists",
            #     "bq_table": "lists",
            #     "description": "List of lists",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # TYPES / LOOKUP TABLES
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/types/attendancetypes",
            #     "bq_table": "types_attendance",
            #     "description": "Types attendance types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/types/excusedurationtypes",
            #     "bq_table": "types_excuse_duration",
            #     "description": "Types excuse duration types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/types/excusedtypes",
            #     "bq_table": "types_excused",
            #     "description": "Types excused types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/types/tables",
            #     "bq_table": "types_tables",
            #     "description": "Types table types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/types/tablevalues",
            #     "bq_table": "types_table_values",
            #     "description": "Types table values",
            #     "flatten_fields": [],
            #     "required_params": {"id": "YOUR_TABLE_ID"},
            # },

            # {
            #     "path": "/v1/types/countries",
            #     "bq_table": "types_countries",
            #     "description": "Types countries",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # TEST SCORES
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/testscores",
            #     "bq_table": "test_scores",
            #     "description": "Test scores by user ID",
            #     "flatten_fields": [],
            #     "required_params": {"user_id": "YOUR_USER_ID"},
            # },

            # {
            #     "path": "/v1/testscores/testtypes",
            #     "bq_table": "test_score_types",
            #     "description": "Test and subtest types",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/testscores/all",
            #     "bq_table": "test_scores_all",
            #     "description": "Test scores (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # MEDICAL
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/medical/securityroles",
            #     "bq_table": "medical_security_roles",
            #     "description": "Medical security roles",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # EVENTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/events/categories",
            #     "bq_table": "events_categories",
            #     "description": "Events categories",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/events/calendar",
            #     "bq_table": "events_calendar",
            #     "description": "Calendar for user",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # SCHEDULE
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/schedules/meetings",
            #     "bq_table": "schedules_meetings",
            #     "description": "Schedules meetings",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # COMMUNITY GROUPS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/communitygroups/rosters",
            #     "bq_table": "community_groups_rosters",
            #     "description": "Community groups rosters",
            #     "flatten_fields": [],
            #     "required_params": {"community_group_id": "YOUR_GROUP_ID"},
            # },

            # ---------------------------------------------------------------
            # DIRECTORIES
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/directories",
            #     "bq_table": "directories",
            #     "description": "Directories",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # CONTENT
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/content/news/categories",
            #     "bq_table": "content_news_categories",
            #     "description": "Content news categories",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/content/news/items",
            #     "bq_table": "content_news_items",
            #     "description": "Content news items",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/content/events/categories",
            #     "bq_table": "content_events_categories",
            #     "description": "Content events categories",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/content/events",
            #     "bq_table": "content_events",
            #     "description": "Content events",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/content/resources",
            #     "bq_table": "content_resources",
            #     "description": "Content resource board",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/content/announcements/categories",
            #     "bq_table": "content_announcement_categories",
            #     "description": "Content announcement categories",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/content/announcements",
            #     "bq_table": "content_announcements",
            #     "description": "Content announcements",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # CONTENT MANAGEMENT
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/contentmanagement/news/categories",
            #     "bq_table": "contentmgmt_news_categories",
            #     "description": "Content management news categories",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/contentmanagement/announcements/categories",
            #     "bq_table": "contentmgmt_announcement_categories",
            #     "description": "Content management announcement categories",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/contentmanagement/photoalbums/categories",
            #     "bq_table": "contentmgmt_photo_album_categories",
            #     "description": "Content management photo album categories",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

        ],
    },

    # ===================================================================
    # ENROLLMENT MANAGEMENT API
    # ===================================================================
    {
        "api_name": "Enrollment Management",
        "base_url": "https://api.sky.blackbaud.com/afe-edems",
        "bq_dataset": "bbem_enrollment_mgmt",
        "endpoints": [

            # ---------------------------------------------------------------
            # CANDIDATES
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/candidates",
            #     "bq_table": "candidates",
            #     "description": "Candidate list",
            #     "flatten_fields": ["user", "entering_year", "entering_grade", "role", "status"],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/candidatestatuses",
            #     "bq_table": "candidate_status_changes",
            #     "description": "Candidate status change list",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # INQUIRIES
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/inquiries",
            #     "bq_table": "inquiries",
            #     "description": "Inquiry list",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # TESTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/tests",
            #     "bq_table": "tests",
            #     "description": "Test list",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # TYPES / LOOKUPS
            # ---------------------------------------------------------------

            # {
            #     "path": "/v1/types/candidatestatuses",
            #     "bq_table": "types_candidate_statuses",
            #     "description": "Candidate status type list",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/types/checkliststatuses",
            #     "bq_table": "types_checklist_statuses",
            #     "description": "Candidate checklist status type list",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/types/studentchecklisttypes",
            #     "bq_table": "types_student_checklist_types",
            #     "description": "Student checklist type list",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/types/checklistTypes",
            #     "bq_table": "types_checklist_types",
            #     "description": "Candidate checklist type list",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/v1/types/interesttypes",
            #     "bq_table": "types_interest_types",
            #     "description": "Interest type list",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # STUDENT CHECKLISTS (require path param — advanced usage)
            # ---------------------------------------------------------------
            # Note: /v1/studentchecklists/{student_id} requires a student ID
            # in the URL path. The current pipeline does not support path
            # parameters. Uncomment only if the pipeline is extended.

        ],
    },

    # ===================================================================
    # ONEROSTER API
    # ===================================================================
    {
        "api_name": "OneRoster",
        "base_url": "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1",
        "bq_dataset": "bbem_oneroster",
        "endpoints": [

            # ---------------------------------------------------------------
            # ACADEMICS
            # ---------------------------------------------------------------

            # {
            #     "path": "/academicSessions",
            #     "bq_table": "academic_sessions",
            #     "description": "Academic sessions (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/terms",
            #     "bq_table": "terms",
            #     "description": "Terms (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/gradingPeriods",
            #     "bq_table": "grading_periods",
            #     "description": "Grading periods (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # CATEGORIES
            # ---------------------------------------------------------------

            # {
            #     "path": "/categories",
            #     "bq_table": "categories",
            #     "description": "Categories (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # CLASSES & COURSES
            # ---------------------------------------------------------------

            # {
            #     "path": "/classes",
            #     "bq_table": "classes",
            #     "description": "Classes (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/courses",
            #     "bq_table": "courses",
            #     "description": "Courses (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # ENROLLMENTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/enrollments",
            #     "bq_table": "enrollments",
            #     "description": "Enrollments (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # LINE ITEMS & RESULTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/lineItems",
            #     "bq_table": "line_items",
            #     "description": "Line items (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/results",
            #     "bq_table": "results",
            #     "description": "Results (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # ORGANIZATIONS & SCHOOLS
            # ---------------------------------------------------------------

            # {
            #     "path": "/orgs",
            #     "bq_table": "orgs",
            #     "description": "Organizations (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/schools",
            #     "bq_table": "schools",
            #     "description": "Schools (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # USERS / TEACHERS / STUDENTS
            # ---------------------------------------------------------------

            # {
            #     "path": "/users",
            #     "bq_table": "users",
            #     "description": "Users (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/teachers",
            #     "bq_table": "teachers",
            #     "description": "Teachers (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # {
            #     "path": "/students",
            #     "bq_table": "students",
            #     "description": "Students (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

            # ---------------------------------------------------------------
            # DEMOGRAPHICS
            # ---------------------------------------------------------------

            # {
            #     "path": "/demographics",
            #     "bq_table": "demographics",
            #     "description": "Demographics (all)",
            #     "flatten_fields": [],
            #     "required_params": {},
            # },

        ],
    },

]
