#include <CoreServices/CoreServices.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

// NOTE: when compiling, add flag: -framework CoreServices

void usage();
void *listen_for_events(void *);
char **build_args(char *,int,char **);
void fs_callback(ConstFSEventStreamRef,void *,size_t,void *,const FSEventStreamEventFlags *,const FSEventStreamEventId *);
void build_callbackInfo(int,char **);

typedef struct ListenerInfo {
    char *path_to_scan;
    char *callback_script;
    char **script_args;
} ListenerInfo;

// global variable containing info about a given instance of the FS listener, as
// read from the command line arguments
ListenerInfo callbackInfo;

int main(int argc, char **argv) 
{
    build_callbackInfo(argc, argv); // populate callbackInfo struct
    CFStringRef format = CFSTR("%s");
    CFStringRef pathRef = CFStringCreateWithFormat(NULL, NULL, format, callbackInfo.path_to_scan);
    CFArrayRef pathsToWatch = CFArrayCreate(NULL, (const void **)&pathRef, 1, NULL);
    FSEventStreamRef stream;
    CFAbsoluteTime latency = .1;
    stream = FSEventStreamCreate(NULL,
            fs_callback,
            NULL,
            pathsToWatch,
            kFSEventStreamEventIdSinceNow,
            latency,
            kFSEventStreamCreateFlagNone);

    pthread_t listener_thread;
    pthread_create(&listener_thread, NULL, listen_for_events, &stream);

    pthread_join(listener_thread, NULL);
    fprintf(stdout, "exiting...\n");
    return 0;
}

void *listen_for_events(void *streamPtr)
{
    assert(streamPtr);
    FSEventStreamRef stream = *(FSEventStreamRef *) streamPtr;
    CFRunLoopGetCurrent();
    FSEventStreamScheduleWithRunLoop(stream, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode);
    FSEventStreamStart(stream);
    fprintf(stdout, "(listening for fs events...)\n");
    CFRunLoopRun();

    return NULL;
}

void build_callbackInfo(int argc, char **argv)
{
    int i;
    if (argc < 3) 
    {
        usage();
    }
    callbackInfo.path_to_scan = argv[1];
    callbackInfo.callback_script = argv[2];
    callbackInfo.script_args = build_args(callbackInfo.callback_script, argc - 2, argv + 2);
    fprintf(stdout, "path to scan: %s\ncallback script: %s\nscript args: [ ",
            callbackInfo.path_to_scan, callbackInfo.callback_script);
    for (i = 0; i < (argc - 2); i++)
    {
        fprintf(stdout, "%s ", callbackInfo.script_args[i]);
    }
    fprintf(stdout, "]\n");
}

char **build_args(char *callback_script, int num_args, char **args)
{
    int i;
    char **argv = calloc(sizeof(void *), num_args + 2);
    if (!argv)
    {
        fprintf(stdout, "error allocating arg array for callback script args...\n");
        exit(1);
    }
    argv[0] = callback_script;
    for (i = 1; i <= num_args; i++)
    {
        argv[i] = args[i];
    }
    argv[num_args + 1] = NULL;
    return argv;
}

void usage() 
{
    fprintf(stdout, "usage: fsListener <path to scan> <callback script> [ callback script arguments ]\n");
    exit(1);
}

void fs_callback(
        ConstFSEventStreamRef streamRef,
        void *clientCallBackInfo,
        size_t numEvents,
        void *eventPaths,
        const FSEventStreamEventFlags eventFlags[],
        const FSEventStreamEventId eventIds[])
{
    int i;
    char **paths = eventPaths;

    printf("Callback called\n");
    for (i=0; i<numEvents; i++) {
        int count;
        /* flags are unsigned long, IDs are uint64_t */
        // fprintf(stdout, "Change %llu in %s, flags %u\n", eventIds[i], paths[i], (unsigned int) eventFlags[i]);
    }
    pid_t pid = fork();
    if (pid == 0)
    {
        execvp(callbackInfo.callback_script, callbackInfo.script_args);
    }
    else
    {
        int status;
        waitpid(pid, &status, 0);
        if (status)
        {
            fprintf(stderr, "exit status from pid %d: %d\n", pid, status);
        }
    }
}
