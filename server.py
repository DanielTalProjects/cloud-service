import os
import random
import socket
import string
import sys
main_dict = {}


"""
#Function Name: handshake
#Input: client_identifier,connection_id,path
#Output: client_identifier,connection_id
#Function Operation: the function sets up the connection between the client and server
"""


def handshake(client_socket):
    has_identifier = client_socket.recv(1).decode("ISO-8859-8","ignore")
    if has_identifier == "n":
        client_identifier = ''.join(random.choices(string.ascii_letters + string.digits, k=128))
        client_socket.send(client_identifier.encode("ISO-8859-8","ignore"))
        print(client_identifier)
        connection_id = ''.join(random.choices(string.ascii_letters + string.digits, k=128))
        client_socket.send(connection_id.encode("ISO-8859-8","ignore"))
        client_dict = {connection_id: []}
        main_dict[client_identifier] = client_dict
        get_all(client_socket, client_identifier)
    if has_identifier == "y":
        client_identifier = client_socket.recv(128).decode("ISO-8859-8","ignore")
        has_connection_id = client_socket.recv(1).decode("ISO-8859-8","ignore")
        if has_connection_id == "n":
            connection_id = ''.join(random.choices(string.ascii_letters + string.digits, k=128))
            client_socket.send(connection_id.encode("ISO-8859-8","ignore"))
            main_dict[client_identifier][connection_id] = []
            send_all(client_socket, client_identifier)
        else:
            connection_id = client_socket.recv(128).decode("ISO-8859-8","ignore")
            send_changes(client_socket, client_identifier, connection_id)
            get_changes(client_socket, client_identifier, connection_id)
    return


"""
#Function Name: get_all
#Input: socket,path
#Output: none
#Function Operation: the function gets all the content of a folder.
"""


def get_all(client_socket, client_identifier):
    folder_name = ""
    while True:
        # recieve in pieces if file too big
        header = client_socket.recv(1).decode("ISO-8859-8","ignore")
        if header == 'e':
            break
        elif header == "d":
            folder_name = get_path(client_socket, client_identifier)
            os.makedirs(folder_name, exist_ok=True)
        elif header == "f":
            get_all_file(client_socket, folder_name)
    return


"""
#Function Name: get_all_file
#Input: socket,folder_name
#Output: none
#Function Operation: the function gets a file, called by the function get_all
"""


def get_all_file(client_socket,folder_name):
    name_length = int.from_bytes(client_socket.recv(4), "little")
    file_name = client_socket.recv(name_length)
    file_path = os.path.join(folder_name, file_name.decode('ISO-8859-8',"ignore"))
    with open(file_path, 'wb') as f:
        chunk_size = int.from_bytes(client_socket.recv(2), "little")
        while chunk_size!=0:
            data = client_socket.recv(chunk_size)
            f.write(data)
            client_socket.send("ack".encode('ISO-8859-8'))
            chunk_size = int.from_bytes(client_socket.recv(2), "little")


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
    # might need to read the file in pieces if bigger than 1 gb
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
#Function Name: send_all
#Input: socket,path
#Output: none
#Function Operation: the function sends all the content of the folder in path
"""


def send_all(s, client_socket):
    count=0
    correct_path = ""
    for dir_path, sub_dirs, files in os.walk(client_socket):
        if count==0:
            count+=1
        else:
            correct_path=os.path.normpath(os.path.relpath(dir_path, client_socket))
        s.send("d".encode("ISO-8859-8","ignore"))  # directory
        send_path(s, correct_path)
        for file_name in files:
            s.send("f".encode("ISO-8859-8","ignore"))  # file
            file_path = os.path.join(dir_path, file_name)
            send_all_file(s, file_name, file_path)
    s.send("e".encode("ISO-8859-8","ignore"))  # end


"""
#Function Name: save_in_dict
#Input: add_action, client_identifier, connection_id
#Output: none
#Function Operation: the function saves in the main dictionary which connection ids need to be updated
#                    on each action made
"""


def save_in_dict(add_action, client_identifier, connection_id):
    for i in main_dict[client_identifier]:
        if i == connection_id:
            continue
        main_dict[client_identifier][i].append(add_action)


"""
#Function Name: get_path
#Input: socket,path
#Output: abs path
#Function Operation: the function gets the path that was sent and returns only the abs path
"""


def get_path(client_socket, client_identifier):
    name_length = int.from_bytes(client_socket.recv(4), "little")
    path_recv = client_socket.recv(name_length).decode("ISO-8859-8","ignore")
    if os.name=="nt":
        path_recv=path_recv.replace("/","\\")
    folder_name = os.path.join(client_identifier, path_recv)
    return folder_name


"""
#Function Name: get_path_double_return
#Input: socket,path
#Output: abs path, relative path
#Function Operation: the function gets the path that was sent and returns the abs path and relative path
"""


def get_path_double_return(client_socket, client_identifier):
    name_length = int.from_bytes(client_socket.recv(4), "little")
    path_recv = client_socket.recv(name_length).decode("ISO-8859-8","ignore")
    if os.name=="nt":
        path_recv=path_recv.replace("/","\\")
    folder_name = os.path.join(client_identifier, path_recv)
    return folder_name,path_recv


"""
#Function Name: send_path
#Input: socket,path
#Output: none
#Function Operation: the function sends the relative path
"""


def send_path(s, correct_path):
    if os.name=="nt":
        correct_path=correct_path.replace("\\","/")
    s.send(len(correct_path).to_bytes(4, 'little'))
    s.send(correct_path.encode("ISO-8859-8","ignore"))
    return


"""
#Function Name: move_change
#Input: old_path,new_path
#Output: none
#Function Operation: the function handles a event of moving a file or folder
"""


def move_change(old_path, new_path):
    if not os.path.exists(old_path):
        return
    if os.path.isfile(old_path):
        os.renames(old_path, new_path)
        return
    os.makedirs(new_path, exist_ok=True)
    count=0
    add_to_path=""
    original_folder = ""
    for root, dirs, files in os.walk(old_path, topdown=True):
        if count==0:
            original_folder=root
            count+=1
        else:
            add_to_path=os.path.normpath(os.path.relpath(root, original_folder))
        for name in files:
            os.rename(os.path.join(root, name), (os.path.join(os.path.join(new_path,add_to_path),name)))
        for name in dirs:
            os.makedirs(os.path.join(os.path.join(new_path, add_to_path), name), exist_ok=True)
    for root, dirs, files in os.walk(old_path, topdown=False):
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    if os.path.exists(old_path):
        os.rmdir(old_path)


"""
#Function Name: get_changes
#Input: socket,path
#Output: none
#Function Operation: the function gets all the updates from a client
"""


def get_changes(client_socket, client_identifier, connection_id):
    header = client_socket.recv(4).decode("ISO-8859-8","ignore")
    while header!="done":
        src_path, src_path_no_identifier = get_path_double_return(client_socket, client_identifier)
        action = client_socket.recv(3).decode("ISO-8859-8","ignore")
        if action == "cre":
            is_directory =  client_socket.recv(1).decode("ISO-8859-8","ignore")
            if is_directory=="t":
                os.makedirs(src_path, exist_ok=True)
            else:
                if not os.path.isdir(os.path.dirname(src_path)):
                    os.makedirs(os.path.dirname(src_path), exist_ok=True)
                get_changes_file(client_socket,src_path_no_identifier,client_identifier)
                # need to add new get_file that will give me the name of the file to join with src_path_no_identifier
            save_in_dict([src_path_no_identifier, action, is_directory], client_identifier, connection_id)
        elif action == "mod":
            is_directory = client_socket.recv(1).decode("ISO-8859-8","ignore")
            os.remove(src_path)
            get_changes_file(client_socket,src_path_no_identifier,client_identifier)
            save_in_dict([src_path_no_identifier, action, is_directory], client_identifier, connection_id)
        elif action == "mov":
            is_directory = client_socket.recv(1).decode("ISO-8859-8","ignore")
            dest_path, dest_path_no_identifier = get_path_double_return(client_socket, client_identifier)
            move_change(src_path, dest_path)
            save_in_dict([src_path_no_identifier, action, is_directory, dest_path_no_identifier], client_identifier,
                         connection_id)
        elif action == "del":
            if not os.path.exists(src_path):
                header = client_socket.recv(4).decode("ISO-8859-8","ignore")
                continue
            if src_path_no_identifier=="":
                return
            if os.path.isfile(src_path):
                os.remove(src_path)
            elif os.path.isdir(src_path):
                for root, dirs, files in os.walk(src_path, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                if os.path.exists(src_path):
                    os.rmdir(src_path)
            save_in_dict([src_path_no_identifier, action], client_identifier, connection_id)
        header = client_socket.recv(4).decode("ISO-8859-8","ignore")


"""
#Function Name: get_changes_file
#Input: socket,path
#Output: none
#Function Operation: the function gets a file that was sent, called by get_changes
"""


def get_changes_file(client_socket,part_path,client_identifier):
    file_path = os.path.join(client_identifier, part_path)
    with open(file_path, 'wb') as f:
        chunk_size = int.from_bytes(client_socket.recv(2), "little")
        while chunk_size!=0:
            data = client_socket.recv(chunk_size)
            f.write(data)
            client_socket.send("ack".encode('ISO-8859-8'))
            chunk_size = int.from_bytes(client_socket.recv(2), "little")


"""
#Function Name: send_changes
#Input: socket
#Output: none
#Function Operation: the function sends all the updates to a client
"""


def send_changes(client_socket, client_identifier, connection_id):
    for change in main_dict[client_identifier][connection_id]:
        src_path = change[0]
        client_socket.send("more".encode("ISO-8859-8","ignore"))
        send_path(client_socket, src_path)
        action = change[1]
        client_socket.send(action.encode("ISO-8859-8","ignore"))
        if action == "cre" or action == "mod":
            if change[2] == "t":  # if directroy
                client_socket.send("t".encode("ISO-8859-8","ignore"))
            else:
                client_socket.send("f".encode("ISO-8859-8","ignore"))
                send_changes_file(client_socket, os.path.join(client_identifier, src_path))
        if action == "mov":
            if change[2] == "t":  # if directroy
                client_socket.send("t".encode("ISO-8859-8","ignore"))
            else:
                client_socket.send("f".encode("ISO-8859-8","ignore"))
            correct_path = change[3]  # send dest_path
            send_path(client_socket, correct_path)
    main_dict[client_identifier][connection_id].clear()
    client_socket.send("done".encode("ISO-8859-8","ignore"))


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
    s.send(chunk_size.to_bytes(2, "little"))


if __name__ == '__main__':
    if len(sys.argv) - 1 != 1:
        sys.exit("Not correct number of arguments")
    port = int(sys.argv[1])
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', port))
    server.listen()
    while True:
        client_socket, client_address = server.accept()
        handshake(client_socket)
        client_socket.close()