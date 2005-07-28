SHELL = /bin/sh

default:
	@echo "usage: \`make rsync-dry' to test"
	@echo "usage: \`make rsync' to upload"
	@echo "usage: \`make rsync-check' to test with checksum"


# /***********************************************************************
# // rsync via ssh (upload)
# // NOTE: you must create a group `pycurl' on your local machine!
# // see also RSYNC_USER below
# ************************************************************************/

RSYNC = rsync
##RSYNC_FLAGS = -av --relative -e ssh
RSYNC_FLAGS = -av --relative --delete --delete-after -e ssh

UNISON = unison
UNISON_FLAGS = -times -perms 0

RSYNC_FILES = \
	htdocs \
	htdocs/download/.htaccess \
	upload

RSYNC_EXCLUDES = \
	'--exclude=CVS/' \
	'--exclude=htdocs/download/' \
	'--exclude=htdocs/favicon.ico' \
	'--exclude=upload/Ignore/' \
	'--exclude=.cvsignore'
UNISON_EXCLUDES = \
	-ignore 'Name CVS' \
	-ignore 'Path download' \
	-ignore 'Name favicon.ico' \
	-ignore 'Name .cvsignore'

RSYNC_USER = kjetilja@shell.sourceforge.net
ifeq ($(USER),mfx)
RSYNC_USER    = mfx@shell.sourceforge.net
RSYNC_FLAGS  += --itemize-changes
UNISON_FLAGS += -servercmd local/bin/unison
endif

RSYNC_TARGET = /home/groups/p/py/pycurl/


rsync: __rsync-clean
	$(RSYNC) $(RSYNC_FLAGS) $(RSYNC_EXCLUDES) $(RSYNC_FILES) $(RSYNC_USER):$(RSYNC_TARGET)

rsync-dry:
	$(MAKE) rsync 'RSYNC=rsync --dry-run'

rsync-check:
	$(MAKE) rsync 'RSYNC=rsync --dry-run -c'

unison: __rsync-clean
	$(UNISON) $(UNISON_FLAGS) $(UNISON_EXCLUDES) htdocs ssh://$(RSYNC_USER)/$(RSYNC_TARGET)/htdocs


# NOTE: CVS does not maintain metadata like owners and file permissions,
#       so we have to care manually
__rsync-clean:
	chgrp -c -R pycurl .
	chmod -c g+r `find . -perm +400 -print`
	chmod -c g+w `find . -perm +200 -print`
	chmod -c g+s `find . -type d -print`
##	chmod -c g+rws `find . -type d -perm -770 -print`
	chmod -c g+rws `find . -type d -print`
	chmod -c o-rwx upload
	-rm -rf `find . -name .xvpics -type d -print`


.PHONY: rsync rsync-dry rsync-check unison __rsync-clean

