%% Getting port automaticaly from a stytra generated temporary file
%fname = dir(fullfile(tempdir, 'stytra_socket_trigger_port.txt'));
fname = fullfile(tempdir,'stytra_socket_trigger_port.txt');
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
fprintf('Communication pipe open\n')
%% Triggering
matlab_socketTrigger_func;

%% Closing communication
fclose(tcomm);