function [] = matlab_socketTrigger_func

% Send signal to Stytra via TCPIP.
% requires a defined tcpip object in the main workspace.

s.TimeSent = posixtime(datetime('now'));
vars = evalin('base', 'who');

for idx = 1:numel(vars)
    
    cond = evalin('base', ['isa(' vars{idx} ', ''Lightsheet'')']);
    if cond && ~strcmp(vars{idx}, 'ans')
        Params = evalin('base', [vars{idx} '.Parameters']);
        s.Study = Params.Study;
        s.Date = Params.Date;
        s.RunName = Params.RunName;
        s.NCycles = Params.NCycles;
        s.NLayers = Params.NLayers;
    end
end

for idx = 1:numel(vars)
    cond = evalin('base', ['isa(' vars{idx} ', ''tcpip'')']);
    if cond && ~strcmp(vars{idx}, 'ans')
        data = jsonencode(s);
        evalin('base', ['fwrite(' vars{idx} ', ''' data ''')']);
        disp('Sent.');
    end
end