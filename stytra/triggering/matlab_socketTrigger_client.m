t = tcpip('localhost',5554);
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