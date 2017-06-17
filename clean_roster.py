import sys
import pandas as pd
import os
import argparse


'''
Take a roster file and 1) Normalize cases, 2)Check for duplicates, 3) Check to make sure that Teacher IDs and
teacher names form a 1:1 relationship and 4) summarize data to see if certain classes have too few students
'''

parser = argparse.ArgumentParser()
parser.add_argument('-o', '--outDir', metavar='outDir',
                    help='Directory for files to be output to (default: ./)', required=False)

parser.add_argument('-i', '--inFile', nargs = '+', metavar='inFile',
                    help='File to be read in', required=True)

parser.add_argument('-ignorePeriod','--ignorePeriod', dest='ignorePeriod', action = 'store_true',
                    help='Does not include period with course (default: False)', required=False)

parser.add_argument('-remove','--remove', dest='remove', action = 'store_true',
                    help='Automatically removes courses with fewer than 5 students (default: False)', required=False)


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


def checkMissing(roster_df,dropPeriod):
    '''
    Determine if the roster file has missing values
    :param roster_df: (DataFrame)
    :param dropPeriod: (bool) whether we can ignore the period section
    '''
    if dropPeriod == True:
        roster_df = roster_df[['StudentID', 'linked_grade', 'teacherfirst', 'teacherlast', 'TeacherID', 'class',
                               'subject','schoolname','email']]

    needQuit = False
    for index, row in roster_df.iterrows():
        hasNulls = pd.isnull(row).tolist()
        if True in hasNulls:
            print "\n--Missing Info: Check row %i in roster file" %(index)
            needQuit = True
    if needQuit:
        sys.exit(1)

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

def check_issues(roster_df):
    '''
    Check to make sure teacher name and Teacher ID is 1:1
    :param roster_df:
    :return: (string) if there is an issue
    '''

    issue = ''

    # Group by name and see if multiple IDs
    teach_names = []
    roster_grouped_teachname = roster_df.groupby(['teachername'])
    for teachname, otherinfo in roster_grouped_teachname:
        id_list = list(otherinfo['TeacherID'].unique())
        id_list = [str(x) for x in id_list]
        if len(id_list) > 1:
            ids = ','.join(id_list)
            teach_names.append(teachname + ' (' + ids + ')')

    # Group by ID and see if multiple names
    teach_ids = []
    roster_grouped_teachid = roster_df.groupby(['TeacherID'])
    for teachid, otherinfo in roster_grouped_teachid:
        name_list = list(otherinfo['teachername'].unique())
        if len(name_list) > 1:
            names = ','.join(name_list)
            teach_ids.append(str(teachid) + ' (' + names + ')')

    # Group by Student and check if multiple grades
    student_ids = []
    roster_grouped_studentid = roster_df.groupby(['StudentID'])
    for studid, otherinfo in roster_grouped_studentid:
        grade_list = list(otherinfo['linked_grade'].unique())
        if len(grade_list) > 1:
            grade_list = [str(x) for x in grade_list]
            grades = ','.join(grade_list)
            student_ids.append(str(studid) + ' (' + grades + ')')

    # Group by course and check if multiple subjects
    courses = []
    roster_grouped_course = roster_df.groupby(['coursename'])
    for course, otherinfo in roster_grouped_course:
        subj_list = list(otherinfo['subject'].unique())
        if len(subj_list) > 1:
            subj_list = [str(x) for x in subj_list]
            subjects = ','.join(subj_list)
            courses.append(str(course) + ' (' + subjects + ')')

    if teach_names:
        issue += '\nThe following teachers have multiple IDs: {}'.format(', '.join(teach_names))

    if teach_ids:
        issue += '\nThe following teacher IDs have multiple names: {}'.format(', '.join(teach_ids))

    if student_ids:
        issue += '\nThe following students have multiple grades: {}'.format(', '.join(student_ids))

    if courses:
        issue += '\nThe following course have multiple subjects: {}'.format(', '.join(courses))


    return issue


def dropDuplicates(roster_df):
    '''
    Drop duplicates and return new de-duped file
    :param roster_df: (DataFrame)
    :return: (DataFrame) de-duped
    '''

    length_before = len(roster_df)
    roster_df = roster_df.drop_duplicates(take_last=True)
    length_dedup = len(roster_df)

    if length_dedup != length_before:
        print >> sys.stdout, "Removed %d duplicate values from roster data" % (length_before - length_dedup)

    return roster_df


def clean(roster_df,ignorePeriod,clean_name,summ_name,remove):
    '''
    Check for the following:
        - Missing values in any column
        - Make sure teacher names, class names, class periods, and subject are all same case (capitalized lower case)
        - Drop any duplicate rows
        - Output warning if multiple IDs for same teacher first, last name
        - Stop script if same teacher ID has multiple teacher first, last name combinations

    :param roster_df: (DataFrame) roster file with the following headers (order matters, names do not for input):
                       Student ID,Grade Level,Teacher First,Teacher Last,Teacher ID,Class Name,Class Period,
                       Subject,School Name,Teacher Email
    :param ignorePeriod (bool) whether to ignore the Period column when making the coursename field
    :return: cleaned DataFrame file
    '''

    # Roster headers for clean file
    roster_headers = ['StudentID', 'linked_grade', 'teacherfirst', 'teacherlast', 'TeacherID', 'class',
                      'period', 'subject','schoolname','email']

    print roster_df.columns
    # Rename columns
    roster_df.columns = roster_headers

   # Check for missing values
    checkMissing(roster_df,ignorePeriod)


    # Remove any white space
    roster_df = removeSpace(roster_df)

    # Normalize cases
    roster_df = normCases(roster_df)

    # Get ride of duplicates
    roster_df = dropDuplicates(roster_df)

    failIssues = []

    # Create full teacher name and select only teachername and teacher id columns
    roster_df['teachername'] = roster_df['teacherfirst'] + " " + roster_df['teacherlast']

    # If necessary, concatenate class and period
    if ignorePeriod:
        roster_df['coursename'] = roster_df['class']
    else:
        roster_df = formCourseName(roster_df)

    #Check 1:1
    check_df = roster_df[['teachername','TeacherID','StudentID','linked_grade','coursename','subject']]
    issues = check_issues(check_df)
    if issues:
        failIssues.append(issues)

    # Apply custom formatting
    #if custom:
    #    roster_df = custom_format_hth(roster_df)

    if failIssues:
        print >> sys.stdout, "The following issues were found in the roster data:\n {}".format('\n'.join(failIssues))
        return "The following issues were found in the roster data:\n {}".format('\n'.join(failIssues))
    else:
        #Drop period column
        roster_df = roster_df[['StudentID', 'linked_grade', 'teacherfirst', 'teacherlast', 'teachername', 'TeacherID',
                               'coursename','subject','schoolname']]
        roster_df, less_five = summarize(roster_df,summ_name,remove)
        if not less_five.empty:
            return "\nThe following courses have too few students:\n%s" % less_five
        else:
            try:
                roster_df.to_csv(clean_name,index=False)
                return ''
            except IOError as e:
                print >> sys.stderr, '\n**ERROR - Cant write to {}. Try closing the file if open.'.format(clean_name)
                return '\n**ERROR - Cant write to {}. Try closing the file if open.'.format(clean_name)

def summarize(roster_df,summ_name,remove):
    '''
    Summarize the number of students in each class

    :param roster_df: (DataFrame) roster file with the following headers: StudentID,linked_grade,teacherfirst,
                                  teacherlast,TeacherID,subject,teachername,coursename
    :return: summarized roster DataFrame
    '''
    less_five = pd.DataFrame()

    # Group by teachername and coursename to determine which courses have fewer than 5 students
    r_grouped = roster_df.groupby(['teachername','coursename']).agg({'StudentID':pd.Series.nunique})
    r_grouped = r_grouped.rename(columns = {'StudentID': 'Enrollment'})
    r_grouped = r_grouped.sort('Enrollment')
    if min(r_grouped['Enrollment'].tolist()) < 5:
        print >> sys.stdout, "\nThe following courses have too few students:\n"
        less_five = r_grouped[r_grouped['Enrollment']<5]
        print >> sys.stdout, less_five

        # If selected, automatically remove those course with fewer than 5 studnets
        if remove:
            print 'Removing courses above from roster file...'
            rows_remove = []
            # Loop through main roster file
            for ix, mainrow in roster_df.iterrows():
                # Loop through dataframe with courses to remove where the index is a tuple of (teacher,course)
                for index, row in less_five.iterrows():
                    if mainrow['coursename'] == index[1] and mainrow['teachername'] == index[0]:
                        rows_remove.append(ix)
            # Only keep those indeces not in the identified rows to remove
            roster_df = roster_df[-(roster_df.index.isin(rows_remove))]

    # Print summary
    if less_five.empty:
        r_grouped.to_csv(summ_name)

    return roster_df, less_five

if __name__ == "__main__":

    args = parser.parse_args()

    # Save in cwd if no output directory specified
    if (args.outDir and not os.path.exists(args.outDir)) or not args.outDir:
        print "No output path or doesn't exist -- will save file here"
        args.outDir = os.getcwd()

    for infile in args.inFile:
        if not os.path.isfile(infile):
            raise IOError('The roster file {} does not exist.'.format(infile))

        try:
            roster = pd.read_csv(infile)
        except:
            raise IOError("The roster file {} could not be opened".format(infile))


        path_noext = os.path.splitext(infile)[0]
        filename = os.path.basename(path_noext)
        print >> sys.stdout, "\n******Cleaning " + filename + "******\n"
        clean_name = filename + '_clean.csv'
        summ_name = filename + '_summary.csv'

        clean_name = os.path.join(args.outDir,clean_name)
        summ_name = os.path.join(args.outDir,summ_name)

        # Output clean version
        clean(roster,args.ignorePeriod,clean_name,summ_name,args.remove)








