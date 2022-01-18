%% Setting port manualy
port = 5556;
%% Getting port automaticaly from a stytra generated temporary file
fname = dir(fullfile(tempdir, 'stytra_socket_trigger_*.txt'));
fname = fullfile(tempdir,fname.name);
fid = fopen(fname,'rt');
port = str2num(fgetl(fid));
fclose(fid);
fprintf('The port number taken from file is : %d \n',port)

%% Opening communication
tcomm = tcpip('localhost',port);
if strcmp(tcomm.status, 'open')
    fclose(tcomm);
end
fopen(tcomm);
%% Triggering
matlab_socketTrigger_func;

%% Closing communication
fclose(tcomm);