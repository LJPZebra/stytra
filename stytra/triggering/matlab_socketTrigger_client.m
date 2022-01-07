fname = dir(fullfile(tempdir, 'stytra_socket_trigger_*.txt'));
fname = fullfile(tempdir,fname.name);
fid = fopen(fname,'rt');
port = str2num(fgetl(fid));
fclose(fid);
fprintf('The port number taken from file is : %d \n',port)
t = tcpip('localhost',port);
if strcmp(t.status, 'open')
    fclose(t);
end
fopen(t);
posixtime(datetime('now'));
%%
s.Width = 800;
s.Height = 600;
s.Title = 'View from the 15th Floor';
s.Animated = false;
s.IDs = [116, 943, 234, 38793];
s.TimeSent = posixtime(datetime('now'));
data = jsonencode(s);
fwrite(t,data);

%%
fclose(t);
%%
