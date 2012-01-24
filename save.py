#!/usr/bin/python
# backs up xfile.xxx to backup/xfile_iii.xxx
import sys, os, shutil, filecmp

backupdir = 'backup'
#msg = ''

try:
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = raw_input('Please enter filename: ').strip()
    
    if os.path.exists(filename):
        root, ext = os.path.splitext(filename)
        new_root  = root.replace(os.path.sep, "_")
        i = 0
        previous = None
        while True:
            ending = '_{i:0>3}{e}'.format(i=i, e=ext)
            target = os.path.join(backupdir, new_root+ending)
            if not os.path.exists(target):
                if ( (previous is not None) and 
                     filecmp.cmp(filename, previous, shallow=False)):
                    print '{0} has already been backed up to {1}.'.format(filename, previous)
                else:
                    shutil.copy2(filename, target)
                    print 'copied {0} to {1}'.format(filename, target)
                break
            else: # target already exists
                previous = target
                i += 1
    else:
        raw_input('ERROR: {0} does not exist...'.format(filename))
except:
    raw_input('some error occured. action aborted.')
#else:
    #print msg
