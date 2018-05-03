import sys
import pandas as pd

'''
Take a roster file and 1) Normalize cases, 2)Check for duplicates, 3) Check to make sure that Teacher IDs and
teacher names form a 1:1 relationship and 4) summarize data to see if certain classes have too few students
'''


def removeSpace(roster_df):
    '''
    Remove extra white space from teacher names and department columns
    :param roster_df:
    :return: (DataFrame)
    '''
    roster_df['teacherfirst'] = roster_df['teacherfirst'].map(str.strip)
    roster_df['teacherlast'] = roster_df['teacherlast'].map(str.strip)
    roster_df['class'] = roster_df['class'].map(str.strip)
    roster_df['subject'] = roster_df['subject'].map(str.strip)
    return roster_df

def normCases(roster_df):
    '''
    Normalize the cases of each column to avoid issues when grouping
    :param roster_df: (DataFrame)
    :return: (DataFrame) new roster with normalized text cases in each column
    '''

    # Each column
    for col in roster_df:
        # Each item
        for ix, item in roster_df[col].iteritems():
            # If string, make all upper case
            if isinstance(item,str):
                parts = item.split(' ')
                new_parts = []
                for part in parts:
                    if col == 'teacherfirst' or col == 'teacherlast' or col == 'schoolname':
                        new_parts.append(part.title())
                    else:
                        new_parts.append(part.upper())
                roster_df[col][ix] = ' '.join(new_parts)
    return roster_df


def dropDuplicates(roster_df):
    '''
    Drop duplicates and return new de-duped file
    :param roster_df: (DataFrame)
    :return: (DataFrame) de-duped
    '''

    length_before = len(roster_df)
    roster_df = roster_df.drop_duplicates(keep='last')
    length_dedup = len(roster_df)

    if length_dedup != length_before:
        print >> sys.stdout, "Removed %d duplicate values from roster data" % (length_before - length_dedup)
    return roster_df


def checkMissing(roster_df, dropPeriod):
    '''
    Determine if the roster file has missing values
    :param roster_df: (DataFrame)
    :param dropPeriod: (bool) whether we can ignore the period section
    '''
    if dropPeriod:
        roster_df = roster_df[['StudentID', 'linked_grade', 'teacherfirst', 'teacherlast', 'TeacherID', 'class',
                               'subject','schoolname','email']]
    issue = []
    for index, row in roster_df.iterrows():
        hasNulls = pd.isnull(row).tolist()
        if True in hasNulls:
            issue.append("\n--Missing Info: Check row %i in roster file" %(index))
    return issue


def check_issues(roster_df):
    '''
    Check to make sure teacher name and Teacher ID is 1:1
    :param roster_df:
    :return: (string) if there is an issue
    '''

    issue = []

    # Group by name and see if multiple IDs
    teach_names = []
    roster_grouped_teachname = roster_df.groupby(['teachername'])
    for teachname, otherinfo in roster_grouped_teachname:
        id_list = list(otherinfo['TeacherID'].unique())
        id_list = [str(x) for x in id_list]
        if len(id_list) > 1:
            ids = ', '.join(id_list)
            teach_names.append([teachname, ids])

    # Group by ID and see if multiple names
    teach_ids = []
    roster_grouped_teachid = roster_df.groupby(['TeacherID'])
    for teachid, otherinfo in roster_grouped_teachid:
        name_list = list(otherinfo['teachername'].unique())
        if len(name_list) > 1:
            names = ', '.join(name_list)
            teach_ids.append([str(teachid), names])

    # Group by Student and check if multiple grades
    student_ids = []
    roster_grouped_studentid = roster_df.groupby(['StudentID'])
    for studid, otherinfo in roster_grouped_studentid:
        grade_list = list(otherinfo['linked_grade'].unique())
        if len(grade_list) > 1:
            grade_list = [str(x) for x in grade_list]
            grades = ', '.join(grade_list)
            student_ids.append([str(studid), grades])

    # Group by course and check if multiple subjects
    courses = []
    roster_grouped_course = roster_df.groupby(['coursename'])
    for course, otherinfo in roster_grouped_course:
        subj_list = list(otherinfo['subject'].unique())
        if len(subj_list) > 1:
            subj_list = [str(x) for x in subj_list]
            subjects = ', '.join(subj_list)
            courses.append([str(course), subjects])

    return teach_names, teach_ids, student_ids, courses


def less_five(roster_df):
    '''
    Group roster data df by teacher and coursename to check that all classes have at least 5 students to survey
    :return: issue
    '''
    issue = []

    # Group by teachername and coursename to determine which courses have fewer than 5 students
    r_grouped = roster_df.groupby(['teachername', 'coursename']).agg({'StudentID': pd.Series.nunique})
    r_grouped = r_grouped.rename(columns={'StudentID': 'Enrollment'})
    r_grouped = r_grouped.sort_values(by='Enrollment')
    if min(r_grouped['Enrollment'].tolist()) < 5:
        issue = [[x, y[0], y[1]] for x, y in zip(r_grouped[r_grouped['Enrollment'] <5]['Enrollment'].values,
                                                 r_grouped[r_grouped['Enrollment'] < 5].index.tolist())]
    return issue


def formCourseName(roster_df):
    '''
    Concatenate course with period in the form 'Course - Period'
    :param roster_df: (DataFrame)
    :return: new DataFrame
    '''

    courses = roster_df['class'].tolist()
    periods = roster_df['period'].tolist()

    coursenames = []

    for course,period in zip(courses,periods):
        new_course = course + " - '" + str(period) + "'"
        coursenames.append(new_course)

    roster_df['coursename'] = coursenames
    return roster_df


def summarize(roster_df, summ_name, to_csv=False):
    '''
    Summarize the number of students in each class
    :param roster_df: (DataFrame) roster file with the following headers: StudentID,linked_grade,teacherfirst,
                                  teacherlast,TeacherID,subject,teachername,coursename
    :return: summarized roster DataFrame
    '''

    # Group by teachername and coursename to determine which courses have fewer than 5 students
    r_grouped = roster_df.groupby(['teachername','coursename']).agg({'StudentID':pd.Series.nunique})
    r_grouped = r_grouped.rename(columns = {'StudentID': 'Enrollment'})
    r_grouped = r_grouped.sort_values(by='Enrollment')

    # Print if explicitly called
    if to_csv:
        r_grouped.to_csv(summ_name)
    return r_grouped


def data_check(roster_df, dropPeriod):
    '''
    Check for and clean up the following:
        - Missing values in any column
        - Make sure teacher names, class names, class periods, and subject are all same case (capitalized lower case)
        - Drop any duplicate rows
    Outputs error for the following:
        - Multiple IDs for same teacher first, last name
        - Same teacher ID has multiple teacher first, last name combinations
        - Less than 5 students being surveyed in the class
    :param roster_df:
    :return: issue
    '''
    issues = {}

    # Roster headers for clean file
    roster_headers = ['StudentID', 'linked_grade', 'teacherfirst', 'teacherlast', 'TeacherID', 'class',
                      'period', 'subject', 'schoolname', 'email']

    # Rename columns
    roster_df.columns = roster_headers

    # Create full teacher name and select only teachername and teacher id columns
    roster_df['teachername'] = roster_df['teacherfirst'] + " " + roster_df['teacherlast']

    # If necessary, concatenate class and period
    if dropPeriod:
        roster_df['coursename'] = roster_df['class']
    else:
        roster_df = formCourseName(roster_df)

    # Check for missing values
    issues["missing"] = checkMissing(roster_df, dropPeriod)

    # Check for any 1:1 issues
    issues["teachmultids"], issues["idmultteach"], issues["stumultgrades"], issues["coursemultsubj"] = check_issues(roster_df)

    # Check for less than 5 students issues
    issues["lessfive"] = less_five(roster_df)

    if not issues:
        # Remove any white space
        roster_df = removeSpace(roster_df)

        # Normalize cases
        roster_df = normCases(roster_df)

        # Get rid of duplicates
        roster_df = dropDuplicates(roster_df)

    return issues, roster_df
