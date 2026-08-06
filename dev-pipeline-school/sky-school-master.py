import apache_beam as beam
from apache_beam.io.requestresponse import (
    Caller, 
    RequestResponseIO, 
    UserCodeExecutionException, 
    UserCodeQuotaException
)
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions
import requests
import json
import logging
from typing import Optional


class SkyApiCaller(Caller):
    """
    A Caller implementation for the Apache Beam requestresponse API 
    to interact with the Blackbaud SKY API.
    """
    def __init__(self, access_token: str, api_subscription_key: Optional[str] = None):
        """
        Initializes the Caller with necessary authentication headers.
        
        Args:
            access_token: The OAuth 2.0 access token for SKY API.
            api_subscription_key: Optional subscription key if your SKY API app requires it (bb-api-subscription-key).
        """
        self.access_token = access_token
        self.api_subscription_key = api_subscription_key
        
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        
        subscription_key = self.api_subscription_key
        if subscription_key is not None:
            self.headers['bb-api-subscription-key'] = subscription_key

    def __call__(self, request: str, *args, **kwargs) -> tuple:
        """
        Executes the web API call to SKY API.
        
        Args:
            request: The full SKY API URL endpoint (e.g., "https://api.sky.blackbaud.com/school/v1/users").
            
        Returns:
            A tuple of (request_url, JSON_response_string).
        """
        try:
            url = request
            logging.info(f"Making request to SKY API: {url}")
            
            response = requests.get(url, headers=self.headers)
            
            # Map specific HTTP status codes to Beam exceptions for proper retry/backoff logic
            if response.status_code == 429:
                # Rate limit hit -> triggers exponential backoff if a Repeater is configured
                raise UserCodeQuotaException(f"Rate limited by SKY API: {response.text}")
            elif response.status_code == 401:
                # Unauthorized (token expired or invalid)
                raise UserCodeExecutionException(f"Unauthorized. Check access token: {response.text}")
            elif 400 <= response.status_code < 500:
                # Other generic client errors
                raise UserCodeExecutionException(f"Client error from SKY API: {response.status_code} - {response.text}")
            elif response.status_code >= 500:
                # Server-side errors
                raise UserCodeExecutionException(f"Server error from SKY API: {response.status_code} - {response.text}")
                
            response.raise_for_status()
            
            return request, response.text
            
        except requests.exceptions.RequestException as e:
            raise UserCodeExecutionException(f"Request failed: {str(e)}")

def run_pipeline():
    """
    Example Beam pipeline demonstrating how to use the SkyApiCaller with RequestResponseIO.
    """
    # Replace with your actual OAuth token. In a production pipeline, this should be fetched securely.
    ACCESS_TOKEN = "your_oauth_access_token_here"
    API_SUBSCRIPTION_KEY = "your_api_subscription_key" # Optional, depending on API requirements
    
    def write_json_file(element):
        url, data = element
        endpoint_name = url.strip('/').split('/')[-1]
        filename = f"/Users/jshwisberg/Desktop/{endpoint_name}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        return element

    # List of endpoints to fetch data from
    requests_to_make = [
        
        ###### Blackbaud SKY API Education Management "School" endpoints
        #### Documentation: https://developer.sky.blackbaud.com/api#api=school

        ## LEVEL 0 (Root)

        # Name: Academic courses
        # Description: Returns a collection of academic courses, filtered by department and/or school level.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsCoursesGet
        # "https://api.sky.blackbaud.com/school/v1/academics/courses", #6.2MB-3/20/2026

        # Name: Academic departments
        # Description: Returns a collection of academic departments.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsDepartmentsGet
        # "https://api.sky.blackbaud.com/school/v1/academics/departments", #18KB-3/19/2026
        
        # Name: Academic Special Days
        # Description: Returns a collection of special days.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsSpecialDaysGet
        # "https://api.sky.blackbaud.com/school/v1/academics/specialdays", #TBD

        # Name: Activities rosters
        # Description: Returns the activity rosters for a selected year. Uses current school year by default.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1ActivitiesRostersGet
        # "https://api.sky.blackbaud.com/school/v1/activities/rosters", #TBD

        # Name: Advisories rosters
        # Description: Returns the Advisory rosters for a selected year. Uses current school year by default.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AdvisoriesRostersGet
        # "https://api.sky.blackbaud.com/school/v1/advisories/rosters", #TBD
        
        # Name: Athletics locations
        # Description: Returns a collection of athletic locations.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsLocationsGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/locations", #340KB-3/19/2026

        # Name: Athletics opponents
        # Description: Returns a collection of athletic opponents.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsOpponentsGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/opponents" #TBD

        # Name: Athletics rosters
        # Description: Returns the athletic rosters for a selected year. Uses current school year by default.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsRostersGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/rosters", #TBD

        # Name: Athletics sports
        # Description: Returns a collection of athletic sports. Use the option season_id to filter results by season.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsSportsGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/sports", #TBD

        # Name: Athletics sports levels
        # Description: Returns a collection of athletic sports levels.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsSportsLevelsGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/sportslevels", #TBD

        # Name: Athletics teams 
        # Description: Returns a collection of athletic teams for the current school year. Use the optional school_year parameter to specify a different year.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsTeamsGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/teams" #16KB-3/20/2026

        # Name: Athletics transportation types
        # Description: Returns a collection of athletic transportation types.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsTransportationTypesGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/transportationtypes", #TBD

        # Name: Athletics venues
        # Description: Returns a collection of athletic venues.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsVenuesGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/venues", #TBD

        # Name: Attendance record
        # Description: Returns a collection of attendance records for a specified day.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AttendanceGet
        # "https://api.sky.blackbaud.com/school/v1/attendance", #TBD

        # Name: Community groups rosters
        # Description: Returns the community group rosters for a selected school year. Uses current school year by default.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1CommunitygroupsRostersGet
        # "https://api.sky.blackbaud.com/school/v1/communitygroups/rosters", #TBD

        # Name: Core buildings
        # Description: Returns a collection of buildings.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1VenuesBuildingsGet
        # "https://api.sky.blackbaud.com/school/v1/venues/buildings", #TBD

        # Name: Core custom fields
        # Description: Returns a collection of admin custom fields.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1CustomfieldsGet
        # "https://api.sky.blackbaud.com/school/v1/customfields", #TBD

        # Name: Core grade levels
        # Description: Returns a collection of core school grade levels.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1GradelevelsGet
        # "https://api.sky.blackbaud.com/school/v1/gradelevels", #TBD

        # Name: Core offering types
        # Description: Returns a collection of core school offering types.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1OfferingtypesGet
        # "https://api.sky.blackbaud.com/school/v1/offeringtypes", #1KB-3/20/2026

        # Name: Core roles
        # Description: Returns a collection of core school user roles.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1RolesGet
        # "https://api.sky.blackbaud.com/school/v1/roles", #not found error

        # Name: Core levels
        # Description: Returns a collection of core school levels.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1LevelsGet
        # "https://api.sky.blackbaud.com/school/v1/levels", #3KB-3/20/2026

        # Name: Core sessions
        # Description: Returns a collection of core school sessions.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1SessionsGet
        # "https://api.sky.blackbaud.com/school/v1/sessions", #TBD

        # Name: Core terms
        # Description: Returns a collection of core school terms.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1TermsGet
        # "https://api.sky.blackbaud.com/school/v1/terms", #TBD

        # Name: Core time zone
        # Description: Returns the timezone for the school.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1TimezoneGet
        # "https://api.sky.blackbaud.com/school/v1/timezone", #TBD

        # Name: Core years
        # Description: Returns a collection of core school years.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1YearsGet
        # "https://api.sky.blackbaud.com/school/v1/years", #9KB-3/20/2026

        # Name: Directories
        # Description: Returns a collection of directories the logged in user has access to Requires at least one of the following roles in the Education Management System
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1DirectoriesGet
        # "https://api.sky.blackbaud.com/school/v1/directories", #TBD

        # Name: List of lists
        # Description: Returns a list of basic or advanced lists the authorized user has access to.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1ListsGet
        # "https://api.sky.blackbaud.com/school/v1/lists", #TBD

        # Name: List single
        # Description: Returns a collection of results from a basic or advanced list. The requested list must have access permissions enabled for a role listed below or the user requesting the list needs read permission to that list.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1ListsGet
        # "https://api.sky.blackbaud.com/school/v1/lists/advanced/{list_id}[?page][&page_size]", #TBD
        
        ## LEVEL 1 (Roots: level, years, rosters, user)
        # Name: Academics assignments for student
        # Description: Returns assignments for a student that are assigned or due within the date range specified.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsByStudent_idAssignmentsGet
        # "https://api.sky.blackbaud.com/school/v1/academics/{student_id}/assignments?start_date=2025-08-01&end_date=2026-06-30", #TBD

        # Name: Academics rosters
        # Description: Returns the academic rosters for a selected year. Uses current school year by default.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsRostersGet
        # "https://api.sky.blackbaud.com/school/v1/academics/rosters?school_year=2025-2026", #57.9MB-3/19/2026

        # Name: Academics master schedule
        # Description: Returns the master schedule for a selected year.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsSchedulesMasterGet
        # "https://api.sky.blackbaud.com/school/v1/academics/schedules/master?level_num=1395&start_date=2025-08-01&end_date=2026-06-30" #616KB-3/20/2026
        
        # Name: Academics schedule sets
        # Description: Returns the schedule sets for a selected level.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsSchedulesSetsBySchedule_set_idGet
        # "https://api.sky.blackbaud.com/school/v1/academics/schedules/sets/{schedule_set_id}" #TBD
        
        # Name: Academics schedule sets by level
        # Description: Returns the schedule sets for a selected level.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsSchedulesSetsGet
        # "https://api.sky.blackbaud.com/school/v1/academics/schedules/sets?level_num={level_num}[&school_year][&group_type]" #TBD

        # Name: Academics sections by school level
        # Description: Returns a collection of academic sections for the specified school level.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsSectionsGet
        # "https://api.sky.blackbaud.com/school/v1/academics/sections?level_num=1395&school_year=2025-2026" #TBD
        
        # Name: Academics sections by teacher
        # Description: Returns a collection of sections for the specified teacher_id.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsTeachersByTeacher_idSectionsGet
        # "https://api.sky.blackbaud.com/school/v1/academics/teachers/{teacher_id}/sections[?school_year]" #TBD

        # Name: Academics sections for student
        # Description: Returns a collection of sections for the specified student_id. The user requesting the information must be the student, parent of the student or faculty member associated with the student.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsStudentByStudent_idSectionsGet
        # "https://api.sky.blackbaud.com/school/v1/academics/student/{student_id}/sections" #TBD

        # Name: Academics student enrollment list
        # Description: Returns a collection of academic enrollments for the specified user_id.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsEnrollmentsByStudent_idGet
        # "https://api.sky.blackbaud.com/school/v1/academics/enrollments/{user_id}" #TBD

        # Name: Activities sections by school level
        # Description: Returns a collection of activity sections for the specified school level.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1ActivitiesSectionsGet
        # "https://api.sky.blackbaud.com/school/v1/activities/sections?level_num=1395" #TBD

        # Name: Advisories sections by school level
        # Description: Returns a collection of advisory sections for the specified school level.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AdvisoriesSectionsGet
        # "https://api.sky.blackbaud.com/school/v1/advisories/sections?level_num=1395" #TBD

        # Name: Athletics highlights by ID
        # Description: Returns an athletic game's highlights for the specified highlight_id.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsHighlightsByHighlight_idGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/highlights/{highlight_id}" #TBD

        # Name: Athletics schedules
        # Description: Returns a collection of athletic games for the current school year.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsSchedulesGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/schedules?start_date=2025-08-01&end_date=2026-06-30" #TBD

        # Name: Athletics team roster
        # Description: Returns a collection of players and coaches for the specified athletic team's ID.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AthleticsTeamsByTeam_idRosterGet
        # "https://api.sky.blackbaud.com/school/v1/athletics/teams/{team_id}/roster" #TBD

        ## LEVEL 2 (requires sections)
        # Name: Academics assignments by section
        # Description: Returns a collection of assignments for the specified section_id.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsSectionsBySection_idAssignmentsGet
        # "https://api.sky.blackbaud.com/school/v1/academics/sections/{section_id}/assignments", #TBD
        
        # Academics graded assignments for student
        # Description: Returns the graded assignments for the specified student_id and their section_id.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsByStudent_idSectionBySection_idGradedassignmentsGet
        # "https://api.sky.blackbaud.com/school/v1/academics/{student_id}/{section_id}/gradedassignments?marking_period_id={marking_period_id}", #TBD

        # Academics student enrollment changes
        # Description: Returns a collection of students with enrollment changes on or after the date parameter.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsEnrollmentsChangesGet
        # "https://api.sky.blackbaud.com/school/v1/academics/enrollments/changes?start_date={start_date}[&end_date]", #TBD

        # Academic students by section
        # Description: Returns a collection of students for the specified section_id.
        # URL: https://developer.sky.blackbaud.com/api#api=school&operation=V1AcademicsSectionsBySection_idStudentsGet
        # "https://api.sky.blackbaud.com/school/v1/academics/sections/{section_id}/students", #TBD

        #FENXT
        #"https://api.sky.blackbaud.com/accountspayable/v1/shipvia", #464B-3/19/2026
        
        #RENXT
        #"https://api.sky.blackbaud.com/constituent/v1/communicationpreferences", missing rnxt.r scope
    ]
    
    #specify runner
    options = PipelineOptions(flags=["--runner=DirectRunner"])
    #options.view_as(SetupOptions).requirements_file = 'requirements.txt'

    with beam.Pipeline(options=options) as pipeline:
        _ = (
            pipeline
            | 'Create Requests' >> beam.Create(requests_to_make)
            | 'Call SKY API' >> RequestResponseIO(
                caller=SkyApiCaller(
                    access_token="access token goes here", 
                    api_subscription_key="subscription key goes here"
                )
            )
            | 'Parse JSON' >> beam.Map(lambda x: (x[0], json.loads(x[1])))
            | 'Write to Desktop' >> beam.Map(write_json_file)
        )

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run_pipeline()
