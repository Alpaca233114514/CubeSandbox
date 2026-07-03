#define _GNU_SOURCE
#include <errno.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
void enter_namespace(void) {
  char *newMntPath;
  newMntPath = getenv("NEED_SET_MNT");
  if (newMntPath && strcmp(newMntPath, "wsl2") == 0) {
      // WSL2: cubelet is re-executed inside an unshared mount namespace.
      // There is no bind-mounted /proc/<pid>/ns/mnt file available, so skip setns.
      return;
  }
  if (newMntPath) {
      int fd = open(newMntPath, O_RDONLY);
      if (fd < 0 || setns(fd, 0) == -1) {
		     fprintf(stderr, "%d:%d setns on mnt namespace failed: %s\n", getppid(),getpid(), strerror(errno));
	         exit(-1);
      } else {
		     //fprintf(stdout, "%d:%d setns on mnt namespace succeeded\n",getppid(),getpid());
      }
      if (fd >= 0) {
          close(fd);
      }
  }else{
      //printf("enter_namespace nothing\n");
  }
  return;
}
