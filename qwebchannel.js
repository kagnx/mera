"use strict";

var QWebChannel = function(transport, initCallback) {
    if (typeof transport !== "object" || typeof transport.send !== "function") {
        console.error("The given transport object: " + transport + " is invalid!");
        return;
    }

    var channel = this;
    this.transport = transport;
    this.send = function(data) {
        channel.transport.send(JSON.stringify(data));
    };
    this.execCallbacks = {};
    this.execId = 0;
    this.objects = {};

    this.transport.onmessage = function(event) {
        var data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        switch (data.type) {
            case 1: // signal
                channel.handleSignal(data);
                break;
            case 2: // response
                channel.handleResponse(data);
                break;
            case 3: // init
                channel.handleInit(data);
                if (initCallback) initCallback(channel);
                break;
            case 4: // property update
                channel.handlePropertyUpdate(data);
                break;
        }
    };

    this.send({ type: 3 });
};

QWebChannel.prototype.handleSignal = function(data) {
    var object = this.objects[data.object];
    if (object) {
        var signal = object[data.signal];
        if (signal) {
            signal.notify.apply(signal, data.args);
        }
    }
};

QWebChannel.prototype.handleResponse = function(data) {
    if (data.id in this.execCallbacks) {
        this.execCallbacks[data.id](data.data);
        delete this.execCallbacks[data.id];
    }
};

QWebChannel.prototype.handleInit = function(data) {
    for (var objectName in data.objects) {
        var object = data.objects[objectName];
        this.objects[objectName] = this.createObject(objectName, object);
    }
};

QWebChannel.prototype.handlePropertyUpdate = function(data) {
    for (var i = 0; i < data.signals.length; ++i) {
        var signal = data.signals[i];
        var object = this.objects[signal.object];
        if (object) {
            var signalObj = object[signal.signal];
            if (signalObj) {
                signalObj.notify.apply(signalObj, signal.args);
            }
        }
    }
    for (var i = 0; i < data.properties.length; ++i) {
        var property = data.properties[i];
        var object = this.objects[property.object];
        if (object) {
            object[property.property] = property.value;
        }
    }
};

QWebChannel.prototype.createObject = function(objectName, objectInfo) {
    var object = { __id__: objectName };
    for (var i = 0; i < objectInfo.signals.length; ++i) {
        var signalInfo = objectInfo.signals[i];
        var signalName = signalInfo[0];
        object[signalName] = {
            connect: function(signalName) {
                return function(callback) {
                    if (typeof callback !== "function") {
                        console.error("Signal callback must be a function.");
                        return;
                    }
                    if (!this.notify) this.notify = function() {};
                    var oldNotify = this.notify;
                    this.notify = function() {
                        oldNotify.apply(this, arguments);
                        callback.apply(this, arguments);
                    };
                };
            }(signalName)
        };
    }
    for (var i = 0; i < objectInfo.methods.length; ++i) {
        var methodInfo = objectInfo.methods[i];
        var methodName = methodInfo[0];
        var methodId = methodInfo[1];
        object[methodName] = function(methodName, methodId) {
            return function() {
                var args = Array.prototype.slice.call(arguments);
                var callback;
                if (args.length > 0 && typeof args[args.length - 1] === "function") {
                    callback = args.pop();
                }
                var id = ++this.execId;
                if (callback) this.execCallbacks[id] = callback;
                this.send({ type: 2, object: this.objects[objectName].__id__, method: methodId, args: args, id: id });
            }.bind(this);
        }.call(this, methodName, methodId);
    }
    return object;
};
