import os
import socket
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

changes = {}
global TIME, STOP, received_changes
received_changes = []
STOP = False
TIME = time.time()


"""
#Function Name: handshake
#Input: client_identifier,connection_id,path
#Output: client_identifier,connection_id
#Function Operation: the function sets up the connection between the client and server
"""


def handshake(client_identifier,connection_id,path):
    global STOP,TIME
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    if client_identifier == "no":
        s.send("n".encode("ISO-8859-8","ignore"))#no
        client_identifier = s.recv(128).decode("ISO-8859-8","ignore")
        connection_id = s.recv(128).decode("ISO-8859-8","ignore")
        send_all(s, path)
        return client_identifier,connection_id
    else:
        s.send("y".encode("ISO-8859-8","ignore"))  # yes
        s.send(client_identifier.encode("ISO-8859-8","ignore"))
        if connection_id == "no":
            s.send("n".encode("ISO-8859-8","ignore"))  # yes
            connection_id = s.recv(128).decode("ISO-8859-8","ignore")
            get_all(s,path)
            return client_identifier, connection_id
        else:
            s.send("y".encode("ISO-8859-8","ignore"))  # yes
            s.send(connection_id.encode("ISO-8859-8","ignore"))
            STOP = True
            get_changes(s, path)
            STOP = False
            TIME = time.time()
            send_changes(s)
    s.close()


"""
#Function Name: send_path
#Input: socket,path
#Output: none
#Function Operation: the function sends the relative path
"""


def send_path(s,correct_path):
    if os.name=="nt":
        correct_path=correct_path.replace("\\","/")
        correct_path = correct_path.replace("\\\\", "/")
    s.send(len(correct_path).to_bytes(4, 'little'))
    s.send(correct_path.encode("ISO-8859-8","ignore"))


"""
#Function Name: get_path
#Input: socket,path
#Output: path
#Function Operation: the function gets the path that was sent
"""


def get_path(client_socket,path):
    name_length = int.from_bytes(client_socket.recv(4), "little")
    path_recv = client_socket.recv(name_length).decode("ISO-8859-8","ignore")
    if os.name=="nt":
        path_recv=path_recv.replace("/","\\")
    folder_name = os.path.join(path, path_recv)
    return folder_name


"""
#Function Name: send_all
#Input: socket,path
#Output: none
#Function Operation: the function sends all the content of the folder in path
"""


def send_all(s,path):
    count=0
    correct_path = ""
    for dir_path, sub_dirs, files in os.walk(path):
        if count==0:
            count+=1
        else:
            correct_path=os.path.normpath(os.path.relpath(dir_path, path))
        s.send("d".encode("ISO-8859-8","ignore"))  # directory
        send_path(s,correct_path)
        for file_name in files:
            file_srt="f"
            s.send(file_srt.encode("ISO-8859-8","ignore"))
            file_path = os.path.join(dir_path, file_name)
            send_all_file(s, file_name, file_path)
    s.send("e".encode("ISO-8859-8","ignore"))  # end


"""
#Function Name: read_in_pieces
#Input: file, chunk_size
#Output: data
#Function Operation: the function reads a file piece by piece and sends each piece of data
"""


def read_in_pieces(f, chunk_size=1024):
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        yield data


"""
#Function Name: send_all_file
#Input: s,file_name,file_path
#Output: none
#Function Operation: the function sends a file, called by the function send_all
"""


def send_all_file(s,file_name,file_path):
    name_length = len(file_name).to_bytes(4, 'little')
    s.send(name_length)
    s.send(file_name.encode("ISO-8859-8","ignore"))
    with open(file_path, 'rb') as f:
        for piece in read_in_pieces(f):
            s.send(len(piece).to_bytes(2,"little"))
            s.send(piece)
            s.recv(3)
    chunk_size = 0
    s.send(chunk_size.to_bytes(2, "little"))


"""
#Function Name: get_all_file
#Input: socket,folder_name
#Output: none
#Function Operation: the function gets a file, called by the function get_all
"""


def get_all_file(client_socket,folder_name):
    name_length = int.from_bytes(client_socket.recv(4), "little")
    file_name = client_socket.recv(name_length)
    file_path = os.path.join(folder_name, file_name.decode('ISO-8859-8'))
    with open(file_path, 'wb') as f:
        chunk_size = int.from_bytes(client_socket.recv(2), "little")
        while chunk_size!=0:
            data = client_socket.recv(chunk_size)
            f.write(data)
            client_socket.send("ack".encode('ISO-8859-8'))
            chunk_size = int.from_bytes(client_socket.recv(2), "little")


"""
#Function Name: get_all
#Input: socket,path
#Output: none
#Function Operation: the function gets all the content of a folder.
"""


def get_all(client_socket,path):
    folder_name=""
    while True:
        # receive in pieces if file too big
        header = client_socket.recv(1).decode("ISO-8859-8","ignore")
        if header == 'e':
            break
        if header == "d":
            folder_name = get_path(client_socket,path)
            os.makedirs(folder_name, exist_ok=True)
        if header == "f":
            get_all_file(client_socket, folder_name)
    return


"""
#Function Name: created
#Input: event
#Output: none
#Function Operation: the function is called when watchdog recognizes a creation of file or folder
"""


def created(event):
    global STOP,received_changes
    if STOP or time.time()-TIME<0.5:
        if event.src_path in received_changes:
            return
    if not os.path.isfile(event.src_path) and not os.path.isdir(event.src_path):
        return
    changes[event.src_path]=["cre",event.is_directory]
    return


"""
#Function Name: deleted
#Input: event
#Output: none
#Function Operation: the function is called when watchdog recognizes a deletion of file or folder
"""


def deleted(event):
    global STOP,received_changes
    if STOP or time.time()-TIME<0.5:
        if event.src_path in received_changes:
            return
    if event.src_path in changes and changes[event.src_path][0]!="mov":
        del changes[event.src_path]
    if event.src_path==path:
        return
    changes[event.src_path] = ["del"]
    return


"""
#Function Name: moved
#Input: event
#Output: none
#Function Operation: the function is called when watchdog recognizes a moving of file or folder
"""


def moved(event):
    global STOP,received_changes
    if STOP or time.time()-TIME<0.5:
        if event.src_path in received_changes:
            return
    if event.src_path in changes:
        if changes[event.src_path][0]=="cre":
            del changes[event.src_path]
            changes[event.dest_path] = ["cre", event.is_directory]
    else:
        changes[event.src_path] = ["mov", event.is_directory,event.dest_path]
    return


"""
#Function Name: modified
#Input: event
#Output: none
#Function Operation: the function is called when watchdog recognizes a modification of file or folder
"""


def modified(event):
    global STOP,received_changes
    if STOP or time.time()-TIME<0.5:
        if event.src_path in received_changes:
            return
    if event.src_path in changes or not os.path.isfile(event.src_path):
        return
    changes[event.src_path] = ["mod", event.is_directory]
    return


"""
#Function Name: move_change
#Input: old_path,new_path
#Output: none
#Function Operation: the function handles a event of moving a file or folder
"""


def move_change(old_path,new_path):
    global received_changes
    if not os.path.exists(old_path):
        return
    if os.path.isfile(old_path):
        received_changes.append(new_path)
        received_changes.append(old_path)
        os.renames(old_path, new_path)
        return
    received_changes.append(new_path)
    os.makedirs(new_path, exist_ok=True)
    count=0
    add_to_path=""
    original_folder=""
    for root, dirs, files in os.walk(old_path, topdown=True):
        if count==0:
            original_folder=root
            count+=1
        else:
            add_to_path=os.path.normpath(os.path.relpath(root, original_folder))
        for name in files:
            src_path=os.path.join(root, name)
            dest_path=os.path.join(os.path.join(new_path,add_to_path),name)
            received_changes.append(src_path)
            received_changes.append(dest_path)
            os.rename(src_path, dest_path)
        for name in dirs:
            received_changes.append(os.path.join(os.path.join(new_path, add_to_path), name))
            os.makedirs(os.path.join(os.path.join(new_path, add_to_path),name), exist_ok=True)
    for root, dirs, files in os.walk(old_path, topdown=False):
        for name in dirs:
            received_changes.append(os.path.join(root, name))
            os.rmdir(os.path.join(root, name))
    if os.path.exists(old_path):
        received_changes.append(old_path)
        os.rmdir(old_path)


"""
#Function Name: get_changes_file
#Input: socket,path
#Output: none
#Function Operation: the function gets a file that was sent, called by get_changes
"""


def get_changes_file(client_socket,file_path):
    with open(file_path, 'wb') as f:
        chunk_size = int.from_bytes(client_socket.recv(2), "little")
        while chunk_size!=0:
            data = client_socket.recv(chunk_size)
            f.write(data)
            client_socket.send("ack".encode('ISO-8859-8'))
            chunk_size = int.from_bytes(client_socket.recv(2), "little")


"""
#Function Name: get_changes
#Input: socket,path
#Output: none
#Function Operation: the function gets all the updates from the server
"""


def get_changes(s,path):
    global received_changes
    received_changes.clear()
    header = s.recv(4).decode("ISO-8859-8","ignore")
    while header!="done":
        src_path= get_path(s,path)
        action = s.recv(3).decode("ISO-8859-8","ignore")
        if action == "cre":
            received_changes.append(src_path)
            is_directory =  s.recv(1).decode("ISO-8859-8","ignore")
            if is_directory=="t":
                os.makedirs(src_path, exist_ok=True)
            else:
                get_changes_file(s,src_path)
        elif action=="mod":
            is_directory = s.recv(1).decode("ISO-8859-8","ignore")
            received_changes.append(src_path)
            os.remove(src_path)
            received_changes.append(src_path)
            get_changes_file(s,src_path)
        elif action == "mov":
            is_directory = s.recv(1).decode("ISO-8859-8","ignore")
            dest_path = get_path(s, path)
            move_change(src_path,dest_path)
        else:
            if not os.path.exists(src_path):
                continue
            if os.path.dirname(src_path) == client_identifier and os.path.basename(src_path) == "":
                return
            if os.path.isfile(src_path):
                received_changes.append(src_path)
                os.remove(src_path)
            elif os.path.isdir(src_path):
                for root, dirs, files in os.walk(src_path, topdown=False):
                    for name in files:
                        received_changes.append(os.path.join(root, name))
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        received_changes.append(os.path.join(root, name))
                        os.rmdir(os.path.join(root, name))
                received_changes.append(src_path)
                os.rmdir(src_path)
        header = s.recv(4).decode("ISO-8859-8","ignore")


"""
#Function Name: send_changes_file
#Input: socket,path
#Output: none
#Function Operation: the function sends a file, called by send_changes
"""


def send_changes_file(s,file_path):
    with open(file_path, 'rb') as f:
        for piece in read_in_pieces(f):
            s.send(len(piece).to_bytes(2,"little"))
            s.send(piece)
            s.recv(3)
    chunk_size = 0
    s.send((chunk_size.to_bytes(2, "little")))


"""
#Function Name: send_changes
#Input: socket
#Output: none
#Function Operation: the function sends all the updates to the server
"""

def send_changes(s):
    for src_path in changes:
        s.send("more".encode("ISO-8859-8","ignore"))
        correct_path=os.path.normpath(os.path.relpath(src_path, path))
        if correct_path==".":
            correct_path=""
        action = changes[src_path][0]
        send_path(s, correct_path)
        s.send(action.encode("ISO-8859-8","ignore"))
        if action=="cre" or action=="mod":
            if changes[src_path][1]:  # if directory
                s.send("t".encode("ISO-8859-8","ignore"))
            else:
                s.send("f".encode("ISO-8859-8","ignore"))
                send_changes_file(s,src_path)
        elif action == "mov":
            if changes[src_path][1]:  # if directory
                s.send("t".encode("ISO-8859-8","ignore"))
            else:
                s.send("f".encode("ISO-8859-8","ignore"))
            correct_path = os.path.normpath(os.path.relpath(changes[src_path][2], path))
            send_path(s, correct_path)
        elif action=="del" and src_path=="":
            continue
    s.send("done".encode("ISO-8859-8","ignore"))


if __name__ == '__main__':
    if len(sys.argv) - 1 == 4:
        client_identifier = "no"
    elif len(sys.argv)-1 == 5:
        client_identifier = str(sys.argv[5])
    else:
        sys.exit("Not correct number of arguments")
    ip = sys.argv[1]
    port = int(sys.argv[2])
    path = str(sys.argv[3])
    sleep_time = float(sys.argv[4])
    connection_id = "no"
    client_identifier, connection_id = handshake(client_identifier, connection_id, path)
    event_handler = FileSystemEventHandler()
    event_handler.on_created = created
    event_handler.on_deleted = deleted
    event_handler.on_moved = moved
    event_handler.on_modified = modified
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(sleep_time)
            handshake(client_identifier, connection_id, path)
            changes.clear()
    except KeyboardInterrupt:
        observer.stop()