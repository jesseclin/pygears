Relevant blog: http://www.anthonyvh.com/2017/10/13/questasim_on_ubuntu/

Error:

In file included from /tools/home/pygears/pygears/sim/dpi/sock.c:1:0:
/usr/include/stdio.h:27:36: fatal error: bits/libc-header-start.h: No such file or directory
 #include <bits/libc-header-start.h>

Fix:

sudo apt-get install gcc-multilib g++-multilib



Error:

ld: /usr/lib/x86_64-linux-gnu/crti.o: unrecognized relocation (0x2a) in section `.init'
ld: final link failed: Bad value

Fix:

cd <ncsim_install_dir>/tools/cdsgcc/gcc/4.8/bin/
mv ld ld_bkp
ln -s /usr/bin/ld ld


Error:
fatal error: sys/cdefs.h: No such file or directory

Fix:
sudo apt install libc6-dev-i386


Error:

In file included from /usr/include/bits/errno.h:26:0,
                 from /usr/include/errno.h:28,
                 from /tools/home/pygears/pygears/sim/dpi/sock.c:2:
/usr/include/linux/errno.h:1:23: fatal error: asm/errno.h: No such file or directory
 #include <asm/errno.h>
                       ^
compilation terminated.
ncsc_run: *E,TBBLDF: Failed to generate object ./INCA_libs/irun.lnx8664.15.20.nc/ncsc_run/ncsc_obj/sock_0.o

Fix:

maybe install:
linux-libc-dev
linux-libc-dev:i386

required for sure:
ln -s /usr/include/asm-generic /usr/include/asm
