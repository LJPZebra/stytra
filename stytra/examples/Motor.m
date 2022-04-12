classdef Motor < handle
    %   Motor is a virtual class
    %   DMAC inherits from motor
    %   Soloist inherits from motor
    
    properties
        handle % handle on the motor
        % for DMAC, it is a serial communication
        % for Soloist, it is a wrapper for Matlab's Soloist
    end
    
    methods
        % the following methods (functions) are implemented in classes that inherit from Motor
        
        % contructor
        % specific to the motor
        
        % defaultSettings
        % set default settings (can be called by constructor)
        
        % moveabs
        % absolution motion to position defined by given angle
        
        % moverel
        % relative motion to current position plus given angle
        
        % stop
        % stops the motor at the current position
        
        % home
        % brings the motor back to the position defined as "angle 0"
        
        % pow
        % disable the motor axis so it can be rotated by hand
        
        % readPos
        % reads the current position of the motor and returns a value in degrees
        
    end
    
end

